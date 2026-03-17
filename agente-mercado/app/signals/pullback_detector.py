"""Detector de pullback a EMA20 — Plan de Trading secciones 12.2 y 13.2."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.signals.market_state import MarketState

log = logging.getLogger(__name__)

# Umbrales de configuración
MIN_RETRACE_PCT = 0.30  # Retroceso mínimo 30% del impulso
EMA20_ZONE_ATR_MULT = 0.25  # Precio debe estar dentro de 0.25 * ATR de la EMA20


@dataclass(frozen=True)
class PullbackResult:
    """Resultado de detección de pullback."""

    is_valid: bool
    retrace_pct: float  # Porcentaje de retroceso (0-1)
    distance_to_ema20: float  # Distancia absoluta precio-EMA20
    distance_to_ema20_atr: float  # Distancia en múltiplos de ATR


class PullbackDetector:
    """Detecta pullbacks a la EMA20 según las reglas del Plan de Trading.

    Condiciones para pullback válido:
    1. Retroceso >= 30% del rango del impulso (swing_high - swing_low)
    2. Precio dentro de ±0.25 ATR de la EMA20
    """

    def detect(
        self,
        market_state: MarketState,
        direction: str,
    ) -> PullbackResult:
        """Detecta si hay un pullback válido a la EMA20.

        Args:
            market_state: Estado actual del mercado
            direction: "LONG" (pullback bajista en tendencia UP)
                      o "SHORT" (pullback alcista en tendencia DOWN)

        Returns:
            PullbackResult con el análisis
        """
        price = market_state.price
        ema20 = market_state.ema20
        atr = market_state.atr14
        impulse_range = market_state.impulse_range

        # Evitar divisiones por cero
        if impulse_range <= 0 or atr <= 0:
            return PullbackResult(
                is_valid=False,
                retrace_pct=0.0,
                distance_to_ema20=abs(price - ema20),
                distance_to_ema20_atr=0.0,
            )

        # Calcular retroceso
        if direction == "LONG":
            # En tendencia alcista, el pullback es la caída desde el swing high
            retrace = market_state.last_swing_high - price
        else:
            # En tendencia bajista, el pullback es la subida desde el swing low
            retrace = price - market_state.last_swing_low

        retrace_pct = retrace / impulse_range if impulse_range > 0 else 0.0

        # Calcular distancia a EMA20
        distance_to_ema20 = abs(price - ema20)
        distance_to_ema20_atr = distance_to_ema20 / atr

        # Verificar condiciones
        retrace_valid = retrace_pct >= MIN_RETRACE_PCT
        in_ema20_zone = distance_to_ema20_atr <= EMA20_ZONE_ATR_MULT

        is_valid = retrace_valid and in_ema20_zone

        if is_valid:
            log.debug(
                "Pullback detectado en %s: retrace=%.1f%%, dist_ema20=%.2f ATR",
                market_state.instrument,
                retrace_pct * 100,
                distance_to_ema20_atr,
            )

        return PullbackResult(
            is_valid=is_valid,
            retrace_pct=retrace_pct,
            distance_to_ema20=distance_to_ema20,
            distance_to_ema20_atr=distance_to_ema20_atr,
        )
