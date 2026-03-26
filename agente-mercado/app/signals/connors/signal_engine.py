"""Motor de señales Connors RSI(2) — S5 Mean Reversion.

Reglas:
- LONG: precio > SMA(200) + RSI(2) < 10
- SHORT: precio < SMA(200) + RSI(2) > 90
- Exit LONG: precio cierra > SMA(5)
- Exit SHORT: precio cierra < SMA(5)
- Stop: 3 × ATR(14)
"""

from __future__ import annotations

import logging

from app.broker.models import Candle
from app.forex.instruments import get_buffer_price
from app.signals.connors.indicators import atr, rsi, sma
from app.signals.context_filters import FilterResult
from app.signals.pullback_detector import PullbackResult
from app.signals.rule_engine import ForexSignal, ImprovementRuleCheck
from app.strategies.registry import StrategyConfig

log = logging.getLogger(__name__)

# Umbrales Connors
RSI_OVERSOLD = 10
RSI_OVERBOUGHT = 90
SMA_TREND_PERIOD = 200
SMA_EXIT_PERIOD = 5
ATR_STOP_MULT = 3.0


class ConnorsSignalGenerator:
    """Genera señales S5 según el sistema RSI(2) de Larry Connors."""

    def __init__(
        self,
        config: StrategyConfig,
        improvement_rules: list[ImprovementRuleCheck] | None = None,
    ) -> None:
        self._config = config
        self._rules = improvement_rules or []

    def scan_entries(
        self,
        candles_data: dict[str, list[Candle]],
    ) -> list[ForexSignal]:
        """Busca condiciones extremas de RSI(2) en instrumentos con tendencia definida.

        Args:
            candles_data: {"EUR_USD": [Candle, ...]} — candles H1
        """
        signals: list[ForexSignal] = []

        for instrument, candles in candles_data.items():
            if instrument not in self._config.instruments:
                continue
            if len(candles) < SMA_TREND_PERIOD + 5:
                continue

            signal = self._check_rsi_extreme(instrument, candles)
            if signal:
                signals.append(signal)

        return signals

    def _check_rsi_extreme(
        self, instrument: str, candles: list[Candle],
    ) -> ForexSignal | None:
        """Detecta RSI(2) en zona extrema con filtro de tendencia SMA(200)."""
        closes = [c.close for c in candles]
        current_price = closes[-1]

        # Filtro de tendencia
        sma200 = sma(closes, SMA_TREND_PERIOD)
        above_sma200 = current_price > sma200
        below_sma200 = current_price < sma200

        # RSI(2)
        rsi_value = rsi(closes, 2)

        # SMA(5) — para calcular TP (exit level)
        sma5 = sma(closes, SMA_EXIT_PERIOD)

        # ATR para stop
        atr_value = atr(candles, 14)
        if atr_value <= 0:
            return None

        buffer = get_buffer_price(instrument)

        # LONG: en uptrend + RSI(2) extremadamente oversold
        if above_sma200 and rsi_value < RSI_OVERSOLD:
            entry = current_price + buffer
            stop = entry - ATR_STOP_MULT * atr_value
            # TP: SMA(5) como objetivo mínimo, al menos 1.5R
            stop_distance = entry - stop
            tp1 = max(sma5, entry + stop_distance * self._config.min_risk_reward)

            log.info(
                "[%s] SEÑAL CONNORS LONG %s — RSI(2)=%.1f SMA200=%.5f price=%.5f entry=%.5f",
                self._config.id, instrument, rsi_value, sma200, current_price, entry,
            )

            return self._build_signal(
                instrument, "LONG", entry, stop, tp1, rsi_value, sma200, candles[-1],
            )

        # SHORT: en downtrend + RSI(2) extremadamente overbought
        if below_sma200 and rsi_value > RSI_OVERBOUGHT:
            entry = current_price - buffer
            stop = entry + ATR_STOP_MULT * atr_value
            stop_distance = stop - entry
            tp1 = min(sma5, entry - stop_distance * self._config.min_risk_reward)

            log.info(
                "[%s] SEÑAL CONNORS SHORT %s — RSI(2)=%.1f SMA200=%.5f price=%.5f entry=%.5f",
                self._config.id, instrument, rsi_value, sma200, current_price, entry,
            )

            return self._build_signal(
                instrument, "SHORT", entry, stop, tp1, rsi_value, sma200, candles[-1],
            )

        # Sin señal — log periódico del RSI(2)
        log.debug(
            "[%s] %s: RSI(2)=%.1f sma200=%s price=%.5f",
            self._config.id, instrument, rsi_value,
            "ABOVE" if above_sma200 else "BELOW", current_price,
        )
        return None

    def _build_signal(
        self,
        instrument: str,
        direction: str,
        entry: float,
        stop: float,
        tp1: float,
        rsi_value: float,
        sma200: float,
        candle: Candle,
    ) -> ForexSignal | None:
        stop_distance = abs(entry - stop)
        if stop_distance <= 0:
            return None

        rr = abs(entry - tp1) / stop_distance
        if rr < self._config.min_risk_reward:
            return None

        filter_result = FilterResult(
            passed=True,
            passed_filters=["sma200_trend", f"rsi2_{rsi_value:.0f}"],
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
            pattern_type=f"CONNORS_RSI2_{direction}",
            entry_price=entry,
            stop_price=stop,
            tp1_price=tp1,
            tp2_price=None,
            risk_reward_ratio=rr,
            confidence=0.65,
            market_state_h1=None,
            market_state_h4=None,
            filter_result=filter_result,
            pullback_result=pullback_result,
            entry_candle=candle,
            entry_timeframe=self._config.entry_timeframe,
        )
