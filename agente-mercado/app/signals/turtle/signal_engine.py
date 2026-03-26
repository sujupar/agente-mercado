"""Motor de señales Turtle Trading — S4 Breakout.

Reglas del sistema Turtle (System 1):
- LONG: precio cierra > Donchian(20) upper
- SHORT: precio cierra < Donchian(20) lower
- Filtro: skip si el breakout previo fue ganador
- Stop: 2 × ATR(20)
- Exit: Donchian(10) inverso (gestionado en orchestrator)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.broker.models import Candle
from app.forex.instruments import get_buffer_price
from app.signals.context_filters import FilterResult
from app.signals.pullback_detector import PullbackResult
from app.signals.rule_engine import ForexSignal, ImprovementRuleCheck
from app.signals.turtle.donchian import calculate_atr, calculate_donchian
from app.strategies.registry import StrategyConfig

log = logging.getLogger(__name__)


class TurtleSignalGenerator:
    """Genera señales S4 según el sistema Turtle Trading."""

    def __init__(
        self,
        config: StrategyConfig,
        improvement_rules: list[ImprovementRuleCheck] | None = None,
        last_breakout_results: dict[str, bool] | None = None,
    ) -> None:
        self._config = config
        self._rules = improvement_rules or []
        # {instrument: True si último breakout fue ganador, False si perdedor}
        self._last_breakout_won = last_breakout_results or {}

    def scan_entries(
        self,
        candles_data: dict[str, list[Candle]],
    ) -> list[ForexSignal]:
        """Busca breakouts en el canal Donchian(20).

        Args:
            candles_data: {"EUR_USD": [Candle, ...]} — candles H4
        """
        signals: list[ForexSignal] = []

        for instrument, candles in candles_data.items():
            if instrument not in self._config.instruments:
                continue
            if len(candles) < 25:
                continue

            signal = self._check_breakout(instrument, candles)
            if signal:
                signals.append(signal)

        return signals

    def _check_breakout(
        self, instrument: str, candles: list[Candle],
    ) -> ForexSignal | None:
        """Detecta breakout Donchian(20) en un instrumento."""
        # Canal de 20 períodos (para entrada)
        dc20 = calculate_donchian(candles, 20)
        if dc20 is None:
            return None

        # Canal de 10 períodos (para calcular TP placeholder)
        dc10 = calculate_donchian(candles, 10)

        # ATR para stop loss
        atr = calculate_atr(candles, 20)
        if atr <= 0:
            return None

        current = candles[-1]
        buffer = get_buffer_price(instrument)

        # Breakout alcista: cierre > upper(20)
        if current.close > dc20.upper:
            # Filtro: skip si el breakout anterior fue ganador
            if self._last_breakout_won.get(f"{instrument}_LONG", False):
                log.info(
                    "[%s] %s: breakout LONG detectado pero SKIP (anterior fue ganador)",
                    self._config.id, instrument,
                )
                return None

            entry = current.close + buffer
            stop = entry - 2 * atr
            stop_distance = entry - stop
            # TP = Donchian(10) lower como referencia, mínimo 2R
            tp1 = entry + max(stop_distance * 2, dc20.upper - dc20.lower)

            return self._build_signal(
                instrument, "LONG", entry, stop, tp1, atr, current,
            )

        # Breakout bajista: cierre < lower(20)
        if current.close < dc20.lower:
            if self._last_breakout_won.get(f"{instrument}_SHORT", False):
                log.info(
                    "[%s] %s: breakout SHORT detectado pero SKIP (anterior fue ganador)",
                    self._config.id, instrument,
                )
                return None

            entry = current.close - buffer
            stop = entry + 2 * atr
            stop_distance = stop - entry
            tp1 = entry - max(stop_distance * 2, dc20.upper - dc20.lower)

            return self._build_signal(
                instrument, "SHORT", entry, stop, tp1, atr, current,
            )

        # Sin breakout
        log.debug(
            "[%s] %s: precio %.5f dentro de Donchian [%.5f - %.5f]",
            self._config.id, instrument, current.close, dc20.lower, dc20.upper,
        )
        return None

    def _build_signal(
        self,
        instrument: str,
        direction: str,
        entry: float,
        stop: float,
        tp1: float,
        atr: float,
        candle: Candle,
    ) -> ForexSignal | None:
        stop_distance = abs(entry - stop)
        if stop_distance <= 0:
            return None

        rr = abs(entry - tp1) / stop_distance
        if rr < self._config.min_risk_reward:
            return None

        log.info(
            "[%s] SEÑAL TURTLE %s %s — entry=%.5f stop=%.5f tp=%.5f R:R=%.1f ATR=%.5f",
            self._config.id, direction, instrument,
            entry, stop, tp1, rr, atr,
        )

        filter_result = FilterResult(
            passed=True,
            passed_filters=["donchian_breakout", "turtle_filter"],
            failed_filters=[],
            total_filters=2,
        )
        pullback_result = PullbackResult(
            is_valid=True, retrace_pct=0,
            distance_to_ema20=0, distance_to_ema20_atr=0,
        )

        return ForexSignal(
            instrument=instrument,
            strategy_id=self._config.id,
            direction=direction,
            pattern_type=f"TURTLE_BREAKOUT_{direction}",
            entry_price=entry,
            stop_price=stop,
            tp1_price=tp1,
            tp2_price=None,
            risk_reward_ratio=rr,
            confidence=0.6,
            market_state_h1=None,
            market_state_h4=None,
            filter_result=filter_result,
            pullback_result=pullback_result,
            entry_candle=candle,
            entry_timeframe=self._config.entry_timeframe,
        )
