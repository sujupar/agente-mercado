"""Analizador de régimen macro — LLM como overlay sobre estrategias cuánticas.

Cada 60 min, usa un LLM (Gemini o Claude) para analizar:
- Velas H4 de los pares principales (EUR_USD, GBP_USD, USD_JPY, XAU_USD)
- Próximos eventos del calendario económico 24h

Output: clasificación de régimen que modula sizing/activación de S1-S5.

FILOSOFÍA: El LLM NO elige trades. Solo responde "¿qué régimen estamos en?".
Esto respeta las capacidades únicas de los LLMs (razonamiento sobre texto,
síntesis cross-asset) y evita sus debilidades (predicción numérica,
consistencia, hallucination en patrones técnicos).

PROVIDERS soportados:
- Gemini (preferido): usa el GeminiClient ya configurado en el sistema,
  comparte budget y rate limits con bitácora/improvement cycles.
- Claude (opcional): fallback si ANTHROPIC_API_KEY está seteada.
- Default_unclear: si ninguno disponible, modo conservador.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.config import settings
from app.db.database import async_session_factory
from app.db.models import RegimeHistory
from app.llm.gemini import GeminiClient
from app.services.economic_calendar import EconomicCalendarService

log = logging.getLogger(__name__)

Regime = Literal["RISK_ON", "RISK_OFF", "TRANSITION", "UNCLEAR"]

# Estrategias disponibles en el sistema (deben coincidir con STRATEGIES registry)
ALL_STRATEGIES = [
    "s1_pullback_20_up",
    "s2_pullback_20_down",
    "s3_ema_crossover",
    "s4_bollinger_reversion",
    "s5_session_breakout",
    "s6_pullback_20_up_m5",
    "s7_pullback_20_down_m5",
    "s8_double_ema_pullback",
    "s9_rsi_ema20",
    "s10_momentum_breakout",
]


@dataclass
class RegimeAnalysis:
    """Resultado del análisis de régimen macro."""

    regime: Regime
    confidence: float  # 0.0 - 1.0
    reasoning: str
    active_strategies: list[str]
    risk_multiplier: float  # 0.0 - 1.5
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    input_data: dict = field(default_factory=dict)

    @classmethod
    def default_unclear(cls, reason: str = "analyzer unavailable") -> "RegimeAnalysis":
        """Estado por defecto conservador cuando el analizador no puede correr."""
        return cls(
            regime="UNCLEAR",
            confidence=0.0,
            reasoning=f"Default: {reason}",
            active_strategies=ALL_STRATEGIES,  # En modo default, todas activas
            risk_multiplier=0.5,
        )

    def is_strategy_active(self, strategy_id: str) -> bool:
        """True si la estrategia está activa en este régimen."""
        if not self.active_strategies:
            return False
        return strategy_id in self.active_strategies


class MacroRegimeAnalyzer:
    """Analiza el régimen macro cada 60 min usando Claude como clasificador."""

    _CACHE_TTL_SECONDS = 3600  # 1 hora
    _MAIN_PAIRS = ["EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD"]

    _PROMPT_TEMPLATE = """Eres un analista macro profesional con 20 años de experiencia operando forex. Tu única tarea es clasificar el régimen ACTUAL del mercado en uno de estos 4 buckets:

**RISK_ON**: flujos hacia activos de riesgo. USD débil en general, EUR/GBP fuertes, yen débil (USD/JPY sube), gold mixto, equities subiendo.

**RISK_OFF**: flujos hacia safe havens. USD fuerte, JPY fuerte (USD/JPY baja), gold fuerte (XAU_USD sube), equities cayendo, bonos subiendo.

**TRANSITION**: el mercado está cambiando de un régimen a otro. Señales mixtas pero con dirección emergente. Típico alrededor de eventos macro (FOMC, NFP).

**UNCLEAR**: sin dirección clara, ruido, sin convicción direccional. Es una respuesta VÁLIDA y frecuente — no operar siempre es sabio.

---

DATOS DE MERCADO (últimas 20 velas H4 por par, más reciente al final):

{pair_data}

---

PRÓXIMOS EVENTOS HIGH-IMPACT EN LAS PRÓXIMAS 24H:

{upcoming_events}

---

INSTRUCCIONES CRÍTICAS:

1. Describe el régimen ACTUAL, no predigas el futuro.
2. Da más peso a la CONSISTENCIA entre pares:
   - EUR/USD sube + GBP/USD sube + USD/JPY sube = USD débil contra EUR/GBP pero yen aún más débil → probable RISK_ON
   - EUR/USD baja + GBP/USD baja + USD/JPY baja + XAU/USD sube = USD débil pero yen fuerte → RISK_OFF clásico
3. Si hay un evento high-impact en <12h, el régimen debe tender a TRANSITION o UNCLEAR con baja confidence. Los mercados se posicionan antes de news.
4. NO quieras operar siempre. UNCLEAR con confidence baja es la respuesta correcta la mayoría del tiempo.
5. Para active_strategies y risk_multiplier, sigue estas reglas:

| Régimen | Confidence | active_strategies | risk_multiplier |
|---------|-----------|-------------------|-----------------|
| RISK_ON | >0.7 | s1_pullback_20_up, s3_ema_crossover, s5_session_breakout | 1.0-1.2 |
| RISK_ON | 0.5-0.7 | s1_pullback_20_up, s3_ema_crossover | 0.7-1.0 |
| RISK_OFF | >0.7 | s2_pullback_20_down, s3_ema_crossover, s4_bollinger_reversion | 0.8-1.0 |
| RISK_OFF | 0.5-0.7 | s2_pullback_20_down, s4_bollinger_reversion | 0.6-0.8 |
| TRANSITION | any | s4_bollinger_reversion (mean reversion funciona en transición) | 0.5 |
| UNCLEAR | any | s3_ema_crossover, s4_bollinger_reversion (ambas con risk bajo) | 0.3 |

6. Si confidence < 0.5, SIEMPRE usa risk_multiplier <= 0.5.

---

Responde SOLO con JSON válido. NO añadas texto antes o después. NO uses code fences.

{{
  "regime": "RISK_ON|RISK_OFF|TRANSITION|UNCLEAR",
  "confidence": 0.0-1.0,
  "reasoning": "explicación breve en español, max 300 chars, cita datos específicos",
  "active_strategies": ["strategy_id_1", "strategy_id_2"],
  "risk_multiplier": 0.0-1.5
}}
"""

    def __init__(
        self,
        broker,
        economic_calendar: EconomicCalendarService,
        gemini_client: GeminiClient | None = None,
    ) -> None:
        self._broker = broker
        self._calendar = economic_calendar
        self._cache: RegimeAnalysis | None = None

        # Provider preference: Gemini > Claude > disabled
        # Gemini: ya tiene GEMINI_API_KEY configurada en Railway, comparte
        #         budget con bitácora/improvement cycles, más barato.
        # Claude: fallback opcional si ANTHROPIC_API_KEY está seteada.
        self._gemini = gemini_client  # puede reutilizarse el instance del orchestrator
        self._anthropic_client = None

        self._provider = self._select_provider()
        self._enabled = self._provider != "none"

        if self._enabled:
            log.info("MacroRegimeAnalyzer provider: %s", self._provider)

    def _select_provider(self) -> str:
        """Selecciona el mejor LLM provider disponible."""
        if settings.gemini_api_key:
            return "gemini"
        if settings.anthropic_api_key:
            return "anthropic"
        return "none"

    def _get_gemini(self) -> GeminiClient | None:
        """Devuelve el cliente Gemini (crea uno propio si no fue inyectado)."""
        if self._gemini is None:
            try:
                self._gemini = GeminiClient()
            except Exception:
                log.exception("Error creando GeminiClient")
                return None
        return self._gemini

    def _get_anthropic(self):
        """Devuelve el cliente Anthropic (lazy init)."""
        if self._anthropic_client is not None:
            return self._anthropic_client
        try:
            from anthropic import AsyncAnthropic
            self._anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            return self._anthropic_client
        except ImportError:
            log.error("anthropic SDK no instalado — disabling Claude provider")
            return None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def provider(self) -> str:
        return self._provider

    def get_current_regime(self) -> RegimeAnalysis:
        """Retorna el régimen cacheado (sync, rápido).

        Usado por el orchestrator en cada tick del entry cycle — NO llama LLM.
        """
        if self._cache is None:
            return RegimeAnalysis.default_unclear("cache vacío")

        age_seconds = (datetime.now(timezone.utc) - self._cache.analyzed_at).total_seconds()

        # Si el cache tiene más de 2× TTL, considerar stale
        if age_seconds > self._CACHE_TTL_SECONDS * 2:
            return RegimeAnalysis.default_unclear(f"cache stale ({age_seconds:.0f}s)")

        return self._cache

    async def analyze(self) -> RegimeAnalysis:
        """Ejecuta un análisis de régimen completo (async, costoso).

        Llamado por el scheduler cada 60 min. Persiste el resultado en DB
        y actualiza el cache en memoria.
        """
        if not self._enabled:
            log.info("Regime analyzer disabled (no LLM API key)")
            return RegimeAnalysis.default_unclear("no API key")

        try:
            pair_data = await self._fetch_pair_data()
            if not pair_data:
                log.warning("Regime analyzer: sin datos de pares")
                return RegimeAnalysis.default_unclear("sin pair data")

            upcoming_events = await self._fetch_upcoming_events()
        except Exception:
            log.exception("Error fetching data for regime analyzer")
            return RegimeAnalysis.default_unclear("error fetching data")

        prompt = self._PROMPT_TEMPLATE.format(
            pair_data=self._format_pair_data(pair_data),
            upcoming_events=self._format_events(upcoming_events),
        )

        # Llamar al LLM provider seleccionado (Gemini o Claude)
        response_text = await self._call_llm(prompt)
        if not response_text:
            return RegimeAnalysis.default_unclear(f"{self._provider} empty response")

        try:
            # Parsear JSON (ambos providers pueden envolver en code fences)
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not match:
                log.warning("Regime analyzer: no JSON in response: %s", response_text[:200])
                return RegimeAnalysis.default_unclear("no JSON in response")

            data = json.loads(match.group(0))
            regime_val = data.get("regime", "UNCLEAR")
            if regime_val not in ("RISK_ON", "RISK_OFF", "TRANSITION", "UNCLEAR"):
                regime_val = "UNCLEAR"

            active_strats = data.get("active_strategies", []) or []
            # Validar que todos los strategy_ids sean reales
            active_strats = [s for s in active_strats if s in ALL_STRATEGIES]

            analysis = RegimeAnalysis(
                regime=regime_val,
                confidence=max(0.0, min(1.0, float(data.get("confidence", 0.0)))),
                reasoning=str(data.get("reasoning", ""))[:500],
                active_strategies=active_strats,
                risk_multiplier=max(0.0, min(1.5, float(data.get("risk_multiplier", 0.5)))),
                input_data={
                    "pairs_count": len(pair_data),
                    "events_count": len(upcoming_events),
                },
            )

            # Enforce rule: confidence < 0.5 → risk_multiplier <= 0.5
            if analysis.confidence < 0.5 and analysis.risk_multiplier > 0.5:
                analysis.risk_multiplier = 0.5

            # Actualizar cache en memoria
            self._cache = analysis

            log.info(
                "Regime: %s (conf=%.2f) mult=%.2f strategies=%s | %s",
                analysis.regime, analysis.confidence, analysis.risk_multiplier,
                analysis.active_strategies, analysis.reasoning[:150],
            )

            # Persistir en DB
            await self._persist(analysis)

            return analysis

        except Exception:
            log.exception("Error parsing regime analysis response")
            return RegimeAnalysis.default_unclear("parse error")

    async def _call_llm(self, prompt: str) -> str:
        """Llama al LLM provider seleccionado y retorna texto de respuesta.

        Gemini: usa generate_text() del GeminiClient existente (response_json=True).
        Claude: usa messages.create() del Anthropic SDK.

        Retorna string vacío si falla.
        """
        if self._provider == "gemini":
            return await self._call_gemini(prompt)
        elif self._provider == "anthropic":
            return await self._call_anthropic(prompt)
        return ""

    async def _call_gemini(self, prompt: str) -> str:
        """Llama a Gemini via GeminiClient existente."""
        client = self._get_gemini()
        if client is None:
            log.error("GeminiClient no disponible para regime analysis")
            return ""
        try:
            # system_prompt = instrucciones, user_prompt = datos
            # Usamos el fallback model (flash) para mantener costo bajo
            text = await client.generate_text(
                system_prompt=(
                    "Eres un analista macro profesional de forex. "
                    "Responde SIEMPRE con JSON válido y nada más."
                ),
                user_prompt=prompt,
                model_override=settings.gemini_fallback_model,
                response_json=True,
            )
            log.info("Gemini regime response length: %d chars", len(text or ""))
            return text or ""
        except Exception:
            log.exception("Error calling Gemini for regime analysis")
            return ""

    async def _call_anthropic(self, prompt: str) -> str:
        """Llama a Claude via Anthropic SDK."""
        client = self._get_anthropic()
        if client is None:
            return ""
        try:
            response = await client.messages.create(
                model=settings.anthropic_vision_model,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text if response.content else ""
            log.info("Claude regime response length: %d chars", len(text))
            return text
        except Exception:
            log.exception("Error calling Claude for regime analysis")
            return ""

    async def _persist(self, analysis: RegimeAnalysis) -> None:
        """Guarda el análisis en la tabla regime_history para auditoría."""
        try:
            async with async_session_factory() as session:
                record = RegimeHistory(
                    timestamp=analysis.analyzed_at,
                    regime=analysis.regime,
                    confidence=analysis.confidence,
                    reasoning=analysis.reasoning,
                    active_strategies=analysis.active_strategies,
                    risk_multiplier=analysis.risk_multiplier,
                    input_data=analysis.input_data,
                )
                session.add(record)
                await session.commit()
        except Exception:
            log.exception("Error persisting regime analysis")

    async def _fetch_pair_data(self) -> dict:
        """Fetch últimas 20 velas H4 de los pares principales."""
        data = {}
        for pair in self._MAIN_PAIRS:
            try:
                candles = await self._broker.get_candles(pair, "H4", 20)
                if candles:
                    data[pair] = candles
            except Exception:
                log.exception("Error fetching %s H4", pair)
        return data

    async def _fetch_upcoming_events(self) -> list:
        """Fetch eventos high-impact en las próximas 24h."""
        try:
            events = await self._calendar.get_events_today()
            now = datetime.now(timezone.utc)
            future_limit = now + timedelta(hours=24)
            return [e for e in events if now <= e.time <= future_limit]
        except Exception:
            log.exception("Error fetching events")
            return []

    def _format_pair_data(self, data: dict) -> str:
        """Formatea candles para el prompt — últimas 10 velas por par."""
        if not data:
            return "(sin datos disponibles)"
        lines = []
        for pair, candles in data.items():
            lines.append(f"\n{pair} (H4, últimas 10 velas):")
            for c in candles[-10:]:
                try:
                    ts = c.timestamp.strftime("%m-%d %H:%M")
                    lines.append(
                        f"  {ts}  O={c.open:.5f} H={c.high:.5f} "
                        f"L={c.low:.5f} C={c.close:.5f}"
                    )
                except Exception:
                    pass
        return "\n".join(lines)

    def _format_events(self, events: list) -> str:
        """Formatea eventos económicos para el prompt."""
        if not events:
            return "(ningún evento high-impact en las próximas 24h)"
        lines = []
        for e in events[:10]:
            try:
                ts = e.time.strftime("%m-%d %H:%M UTC")
                lines.append(f"- {ts}  {e.currency}  {e.title}")
            except Exception:
                pass
        return "\n".join(lines) if lines else "(error formateando eventos)"
