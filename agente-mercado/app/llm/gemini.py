"""Implementación Gemini — cliente LLM para análisis post-trade (bitácora, mejora)."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time

import httpx

from app.config import settings
from app.llm.base import LLMClient

log = logging.getLogger(__name__)


def _redact_log(text: str, max_len: int = 500) -> str:
    """Recorta y redacta datos sensibles de logs."""
    sensitive = {"api_key", "secret", "password", "private_key", "token"}
    for field in sensitive:
        if field in text.lower():
            text = text.replace(text, "[REDACTED]")
    return text[:max_len] + ("..." if len(text) > max_len else "")


class GeminiClient(LLMClient):
    """Cliente para Gemini con fallback automático."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=90.0)
        self._model = settings.gemini_model
        self._fallback_model = settings.gemini_fallback_model

    def _build_url(self, model: str) -> str:
        return f"{self.BASE_URL}/models/{model}:generateContent"

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model_override: str | None = None,
        response_json: bool = False,
    ) -> str:
        """Genera texto con Gemini. Usado para bitácora y ciclos de mejora.

        Args:
            system_prompt: Instrucciones de sistema.
            user_prompt: Prompt del usuario con datos.
            model_override: Modelo específico a usar.
            response_json: Si True, solicita respuesta JSON.

        Returns:
            Texto generado por el modelo.
        """
        if not settings.gemini_api_key:
            log.error("GEMINI_API_KEY no configurada")
            return ""

        prompt_hash = hashlib.sha256(user_prompt.encode()).hexdigest()[:16]

        gen_config = {
            "temperature": settings.gemini_temperature,
            "maxOutputTokens": settings.gemini_max_output_tokens,
        }
        if response_json:
            gen_config["responseMimeType"] = "application/json"

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": user_prompt}]},
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": gen_config,
        }

        start_time = time.monotonic()
        current_model = model_override or self._model
        switched_to_fallback = False

        for attempt in range(4):
            try:
                url = self._build_url(current_model)
                log.info(
                    "Llamando a Gemini modelo=%s (intento %d, hash=%s)",
                    current_model, attempt + 1, prompt_hash,
                )

                resp = await self._client.post(
                    url,
                    params={"key": settings.gemini_api_key},
                    json=payload,
                )

                if resp.status_code in (429, 503):
                    error_type = "Rate limited" if resp.status_code == 429 else "Servicio no disponible"
                    if not switched_to_fallback and current_model != self._fallback_model:
                        log.warning(
                            "%s (HTTP %d) con %s. Cambiando a fallback: %s",
                            error_type, resp.status_code,
                            current_model, self._fallback_model,
                        )
                        current_model = self._fallback_model
                        switched_to_fallback = True
                        await asyncio.sleep(2)
                        continue
                    else:
                        wait = 2 ** (attempt + 1)
                        log.warning(
                            "%s (HTTP %d) con %s, esperando %ds",
                            error_type, resp.status_code, current_model, wait,
                        )
                        await asyncio.sleep(wait)
                        continue

                resp.raise_for_status()
                elapsed = time.monotonic() - start_time

                response_data = resp.json()

                usage = response_data.get("usageMetadata", {})
                log.info(
                    "Gemini respondió en %.1fs | modelo=%s | tokens_in=%s tokens_out=%s",
                    elapsed, current_model,
                    usage.get("promptTokenCount", "?"),
                    usage.get("candidatesTokenCount", "?"),
                )

                candidates = response_data.get("candidates", [])
                if not candidates:
                    log.error("Gemini: sin candidates en respuesta")
                    return ""

                candidate = candidates[0]
                all_parts = candidate.get("content", {}).get("parts", [])
                if not all_parts:
                    log.error("Gemini: sin parts en respuesta")
                    return ""

                # Filtrar solo parts con texto (no thinking)
                text_parts = [
                    p for p in all_parts
                    if "text" in p and not p.get("thought", False)
                ]
                if not text_parts:
                    text_parts = [p for p in all_parts if "text" in p]

                if not text_parts:
                    log.error("Gemini: parts sin texto")
                    return ""

                text = text_parts[0].get("text", "")

                # Limpiar markdown wrappers
                clean_text = text.strip()
                if clean_text.startswith("```"):
                    lines = clean_text.split("\n")
                    clean_text = "\n".join(
                        line for line in lines if not line.strip().startswith("```")
                    )

                return clean_text

            except httpx.HTTPStatusError as e:
                log.error(
                    "Gemini HTTP error %d: %s",
                    e.response.status_code, _redact_log(e.response.text),
                )
                if not switched_to_fallback and current_model != self._fallback_model:
                    current_model = self._fallback_model
                    switched_to_fallback = True
                    await asyncio.sleep(2)
                elif attempt < 3:
                    await asyncio.sleep(2 ** (attempt + 1))
            except Exception:
                log.exception("Error inesperado llamando a Gemini (modelo=%s)", current_model)
                return ""

        return ""

    async def close(self) -> None:
        await self._client.aclose()
