"""8 filtros de contexto obligatorios — Plan de Trading secciones 12.1 y 13.1."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.signals.market_state import MarketState

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FilterResult:
    """Resultado de la evaluación de filtros de contexto."""

    passed: bool
    passed_filters: list[str]
    failed_filters: list[str]
    total_filters: int = 8

    @property
    def pass_rate(self) -> float:
        return len(self.passed_filters) / self.total_filters if self.total_filters > 0 else 0.0


class ContextFilterEngine:
    """Evalúa los 8 filtros de contexto obligatorios del Plan de Trading.

    Para S1_PULLBACK_20_UP (longs):
        1. trend_state_H1 == "UP"
        2. trend_state_H4 != "DOWN"
        3. price > SMA200 en H1
        4. EMA20 > SMA200 en H1
        5. sma200_slope_H1 == "UP" (o "FLAT")
        6. ema20_slope_H1 == "UP" (o "FLAT")
        7. ma_state_H1 != "WIDE"
        8. trap_zone_H1 == False

    Para S2_PULLBACK_20_DOWN (shorts): todo invertido.

    TODOS deben pasar. Si cualquiera falla → no se busca señal.
    """

    def check_all_filters(
        self,
        state_h1: MarketState,
        state_h4: MarketState | None,
        direction: str,
    ) -> FilterResult:
        """Evalúa los 8 filtros de contexto.

        Args:
            state_h1: MarketState del timeframe H1 (primario)
            state_h4: MarketState del timeframe H4 (contexto). Si None, filtros H4 pasan.
            direction: "LONG" o "SHORT"

        Returns:
            FilterResult con detalle de filtros pasados y fallados
        """
        if direction == "LONG":
            return self._check_long_filters(state_h1, state_h4)
        elif direction == "SHORT":
            return self._check_short_filters(state_h1, state_h4)
        else:
            return FilterResult(
                passed=False,
                passed_filters=[],
                failed_filters=[f"Dirección inválida: {direction}"],
            )

    def _check_long_filters(
        self, h1: MarketState, h4: MarketState | None
    ) -> FilterResult:
        passed = []
        failed = []

        # 1. trend_state_H1 == "UP"
        if h1.trend_state == "UP":
            passed.append("1_trend_h1_up")
        else:
            failed.append(f"1_trend_h1_up (actual: {h1.trend_state})")

        # 2. trend_state_H4 != "DOWN"
        if h4 is None or h4.trend_state != "DOWN":
            passed.append("2_trend_h4_not_down")
        else:
            failed.append(f"2_trend_h4_not_down (actual: {h4.trend_state})")

        # 3. price > SMA200
        if h1.price_vs_sma200 == "ABOVE":
            passed.append("3_price_above_sma200")
        else:
            failed.append(f"3_price_above_sma200 (actual: {h1.price_vs_sma200})")

        # 4. EMA20 > SMA200
        if h1.ema20_vs_sma200 == "ABOVE":
            passed.append("4_ema20_above_sma200")
        else:
            failed.append(f"4_ema20_above_sma200 (actual: {h1.ema20_vs_sma200})")

        # 5. sma200_slope == "UP" o "FLAT"
        if h1.sma200_slope in ("UP", "FLAT"):
            passed.append("5_sma200_slope_up")
        else:
            failed.append(f"5_sma200_slope_up (actual: {h1.sma200_slope})")

        # 6. ema20_slope == "UP" o "FLAT"
        if h1.ema20_slope in ("UP", "FLAT"):
            passed.append("6_ema20_slope_up")
        else:
            failed.append(f"6_ema20_slope_up (actual: {h1.ema20_slope})")

        # 7. ma_state != "WIDE"
        if h1.ma_state != "WIDE":
            passed.append("7_ma_not_wide")
        else:
            failed.append(f"7_ma_not_wide (actual: {h1.ma_state})")

        # 8. trap_zone == False
        if not h1.trap_zone:
            passed.append("8_no_trap_zone")
        else:
            failed.append("8_no_trap_zone (TRAP ZONE DETECTED)")

        all_passed = len(failed) == 0

        if not all_passed:
            log.debug(
                "Filtros LONG fallidos para %s: %s",
                h1.instrument,
                ", ".join(failed),
            )

        return FilterResult(passed=all_passed, passed_filters=passed, failed_filters=failed)

    def _check_short_filters(
        self, h1: MarketState, h4: MarketState | None
    ) -> FilterResult:
        passed = []
        failed = []

        # 1. trend_state_H1 == "DOWN"
        if h1.trend_state == "DOWN":
            passed.append("1_trend_h1_down")
        else:
            failed.append(f"1_trend_h1_down (actual: {h1.trend_state})")

        # 2. trend_state_H4 != "UP"
        if h4 is None or h4.trend_state != "UP":
            passed.append("2_trend_h4_not_up")
        else:
            failed.append(f"2_trend_h4_not_up (actual: {h4.trend_state})")

        # 3. price < SMA200
        if h1.price_vs_sma200 == "BELOW":
            passed.append("3_price_below_sma200")
        else:
            failed.append(f"3_price_below_sma200 (actual: {h1.price_vs_sma200})")

        # 4. EMA20 < SMA200
        if h1.ema20_vs_sma200 == "BELOW":
            passed.append("4_ema20_below_sma200")
        else:
            failed.append(f"4_ema20_below_sma200 (actual: {h1.ema20_vs_sma200})")

        # 5. sma200_slope == "DOWN" o "FLAT"
        if h1.sma200_slope in ("DOWN", "FLAT"):
            passed.append("5_sma200_slope_down")
        else:
            failed.append(f"5_sma200_slope_down (actual: {h1.sma200_slope})")

        # 6. ema20_slope == "DOWN" o "FLAT"
        if h1.ema20_slope in ("DOWN", "FLAT"):
            passed.append("6_ema20_slope_down")
        else:
            failed.append(f"6_ema20_slope_down (actual: {h1.ema20_slope})")

        # 7. ma_state != "WIDE"
        if h1.ma_state != "WIDE":
            passed.append("7_ma_not_wide")
        else:
            failed.append(f"7_ma_not_wide (actual: {h1.ma_state})")

        # 8. trap_zone == False
        if not h1.trap_zone:
            passed.append("8_no_trap_zone")
        else:
            failed.append("8_no_trap_zone (TRAP ZONE DETECTED)")

        all_passed = len(failed) == 0

        if not all_passed:
            log.debug(
                "Filtros SHORT fallidos para %s: %s",
                h1.instrument,
                ", ".join(failed),
            )

        return FilterResult(passed=all_passed, passed_filters=passed, failed_filters=failed)
