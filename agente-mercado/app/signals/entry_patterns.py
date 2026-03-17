"""Patrones de entrada Oliver Vélez — 6 patrones exactos del Plan de Trading."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.broker.models import Candle

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PatternResult:
    """Resultado de una detección de patrón."""

    pattern_type: str  # Nombre del patrón
    direction: str  # "LONG" o "SHORT"
    entry_price: float  # Precio de entrada sugerido (high/low del patrón + buffer)
    stop_price: float  # Precio de stop sugerido (low/high del patrón - buffer)
    pattern_high: float  # Máximo del patrón
    pattern_low: float  # Mínimo del patrón
    confidence: float = 0.7  # Confianza base del patrón


class EntryPatternDetector:
    """Detecta los 6 patrones de entrada del Plan de Trading de Oliver Vélez.

    Patrones alcistas (para S1):
        - BULL_ENGULFING
        - PIN_BAR_ALCISTA
        - GREEN_OVERPOWERS_RED

    Patrones bajistas (para S2):
        - BEAR_ENGULFING
        - PIN_BAR_BAJISTA
        - RED_OVERPOWERS_GREEN
    """

    def detect_all(
        self,
        candles: list[Candle],
        direction: str,
    ) -> list[PatternResult]:
        """Detecta todos los patrones válidos en las últimas 3 velas.

        Args:
            candles: Lista de velas (al menos 3)
            direction: "LONG" o "SHORT"

        Returns:
            Lista de patrones detectados (puede estar vacía)
        """
        if len(candles) < 3:
            return []

        results = []

        if direction == "LONG":
            for detector in (
                self.detect_bull_engulfing,
                self.detect_pin_bar_alcista,
                self.detect_green_overpowers_red,
            ):
                result = detector(candles)
                if result:
                    results.append(result)

        elif direction == "SHORT":
            for detector in (
                self.detect_bear_engulfing,
                self.detect_pin_bar_bajista,
                self.detect_red_overpowers_green,
            ):
                result = detector(candles)
                if result:
                    results.append(result)

        return results

    # ── Patrones Alcistas (S1) ──────────────────────────────

    def detect_bull_engulfing(self, candles: list[Candle]) -> PatternResult | None:
        """BULL_ENGULFING: Vela verde engulle vela roja previa.

        Condiciones (del Plan de Trading sección 12.3-A):
        - Vela actual (n) es verde
        - Vela previa (n-1) es roja
        - Cuerpo de n > cuerpo de n-1
        - Close de n > high de n-1
        """
        n = candles[-1]
        n1 = candles[-2]

        if not (n.is_green and n1.is_red):
            return None

        if n.body <= n1.body:
            return None

        if n.close <= n1.high:
            return None

        return PatternResult(
            pattern_type="BULL_ENGULFING",
            direction="LONG",
            entry_price=n.high,
            stop_price=min(n.low, n1.low),
            pattern_high=n.high,
            pattern_low=min(n.low, n1.low),
            confidence=0.75,
        )

    def detect_pin_bar_alcista(self, candles: list[Candle]) -> PatternResult | None:
        """PIN_BAR_ALCISTA: Mecha inferior larga, cierre arriba.

        Condiciones (del Plan de Trading sección 12.3-B):
        - Mecha inferior >= 2x cuerpo
        - Close > low + 0.66 * rango
        """
        n = candles[-1]

        if n.range == 0:
            return None

        if n.body == 0:
            # Doji — no califica como pin bar
            return None

        if n.lower_wick < 2 * n.body:
            return None

        if n.close <= n.low + 0.66 * n.range:
            return None

        return PatternResult(
            pattern_type="PIN_BAR_ALCISTA",
            direction="LONG",
            entry_price=n.high,
            stop_price=n.low,
            pattern_high=n.high,
            pattern_low=n.low,
            confidence=0.70,
        )

    def detect_green_overpowers_red(self, candles: list[Candle]) -> PatternResult | None:
        """GREEN_OVERPOWERS_RED: Verde domina a roja previa.

        Condiciones (del Plan de Trading sección 12.3-C):
        - Vela actual verde, previa roja
        - Rango de n >= 0.7 * rango de n-1
        - Close de n > midpoint de n-1 (low_n1 + 0.5 * rango_n1)
        """
        n = candles[-1]
        n1 = candles[-2]

        if not (n.is_green and n1.is_red):
            return None

        if n1.range == 0:
            return None

        if n.range < 0.7 * n1.range:
            return None

        midpoint_n1 = n1.low + 0.5 * n1.range
        if n.close <= midpoint_n1:
            return None

        return PatternResult(
            pattern_type="GREEN_OVERPOWERS_RED",
            direction="LONG",
            entry_price=n.high,
            stop_price=min(n.low, n1.low),
            pattern_high=n.high,
            pattern_low=min(n.low, n1.low),
            confidence=0.65,
        )

    # ── Patrones Bajistas (S2) ──────────────────────────────

    def detect_bear_engulfing(self, candles: list[Candle]) -> PatternResult | None:
        """BEAR_ENGULFING: Vela roja engulle vela verde previa.

        Condiciones (del Plan de Trading sección 13.3-A):
        - Vela actual (n) es roja
        - Vela previa (n-1) es verde
        - Cuerpo de n > cuerpo de n-1
        - Close de n < low de n-1
        """
        n = candles[-1]
        n1 = candles[-2]

        if not (n.is_red and n1.is_green):
            return None

        if n.body <= n1.body:
            return None

        if n.close >= n1.low:
            return None

        return PatternResult(
            pattern_type="BEAR_ENGULFING",
            direction="SHORT",
            entry_price=n.low,
            stop_price=max(n.high, n1.high),
            pattern_high=max(n.high, n1.high),
            pattern_low=n.low,
            confidence=0.75,
        )

    def detect_pin_bar_bajista(self, candles: list[Candle]) -> PatternResult | None:
        """PIN_BAR_BAJISTA: Mecha superior larga, cierre abajo.

        Condiciones (del Plan de Trading sección 13.3-B):
        - Mecha superior >= 2x cuerpo
        - Close < high - 0.66 * rango
        """
        n = candles[-1]

        if n.range == 0:
            return None

        if n.body == 0:
            return None

        if n.upper_wick < 2 * n.body:
            return None

        if n.close >= n.high - 0.66 * n.range:
            return None

        return PatternResult(
            pattern_type="PIN_BAR_BAJISTA",
            direction="SHORT",
            entry_price=n.low,
            stop_price=n.high,
            pattern_high=n.high,
            pattern_low=n.low,
            confidence=0.70,
        )

    def detect_red_overpowers_green(self, candles: list[Candle]) -> PatternResult | None:
        """RED_OVERPOWERS_GREEN: Roja domina a verde previa.

        Condiciones (del Plan de Trading sección 13.3-C):
        - Vela actual roja, previa verde
        - Rango de n >= 0.7 * rango de n-1
        - Close de n < midpoint de n-1 (low_n1 + 0.5 * rango_n1)
        """
        n = candles[-1]
        n1 = candles[-2]

        if not (n.is_red and n1.is_green):
            return None

        if n1.range == 0:
            return None

        if n.range < 0.7 * n1.range:
            return None

        midpoint_n1 = n1.low + 0.5 * n1.range
        if n.close >= midpoint_n1:
            return None

        return PatternResult(
            pattern_type="RED_OVERPOWERS_GREEN",
            direction="SHORT",
            entry_price=n.low,
            stop_price=max(n.high, n1.high),
            pattern_high=max(n.high, n1.high),
            pattern_low=n.low,
            confidence=0.65,
        )
