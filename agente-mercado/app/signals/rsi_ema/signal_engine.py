"""Motor de señales S9 — RSI + EMA20 Confluencia.

Condiciones (3):
1. RSI(14) ≤ 35 para LONG o ≥ 65 para SHORT (zonas de interés, no extremo)
2. Precio dentro de 0.7 ATR de EMA20
3. EMA20 slope confirma dirección

SL: 1.5 × ATR, TP: 2.0 × ATR
"""

from __future__ import annotations

import logging

from app.broker.models import Candle
from app.forex.instruments import get_buffer_price
from app.signals.context_filters import FilterResult
from app.signals.indicators import atr, ema, rsi
from app.signals.pullback_detector import PullbackResult
from app.signals.rule_engine import ForexSignal, ImprovementRuleCheck
from app.strategies.registry import StrategyConfig

log = logging.getLogger(__name__)

RSI_OVERSOLD = 35
RSI_OVERBOUGHT = 65


class RSIEma20Generator:
    def __init__(self, config: StrategyConfig, improvement_rules: list[ImprovementRuleCheck] | None = None) -> None:
        self._config = config
        self._rules = improvement_rules or []

    def scan_entries(self, candles_data: dict[str, list[Candle]]) -> list[ForexSignal]:
        signals: list[ForexSignal] = []
        for instrument, candles in candles_data.items():
            if instrument not in self._config.instruments:
                continue
            if len(candles) < 30:
                continue
            signal = self._detect(instrument, candles)
            if signal and self._passes_rules(signal):
                signals.append(signal)
        return signals

    def _detect(self, instrument: str, candles: list[Candle]) -> ForexSignal | None:
        closes = [c.close for c in candles]
        current = candles[-1]
        ema20 = ema(closes, 20)
        ema20_prev = ema(closes[:-5], 20)
        atr_val = atr(candles, 14)
        rsi_val = rsi(closes, 14)

        if atr_val <= 0:
            return None

        # Precio cerca de EMA20
        dist = abs(current.close - ema20)
        if dist > 0.7 * atr_val:
            return None

        direction = None
        # LONG: RSI oversold + EMA20 rising
        if rsi_val <= RSI_OVERSOLD and ema20 > ema20_prev:
            direction = "LONG"
        # SHORT: RSI overbought + EMA20 falling
        elif rsi_val >= RSI_OVERBOUGHT and ema20 < ema20_prev:
            direction = "SHORT"

        if direction is None:
            return None

        buffer = get_buffer_price(instrument)
        if direction == "LONG":
            entry = current.close + buffer
            stop = entry - 1.5 * atr_val
            tp1 = entry + 2.0 * atr_val
        else:
            entry = current.close - buffer
            stop = entry + 1.5 * atr_val
            tp1 = entry - 2.0 * atr_val

        stop_distance = abs(entry - stop)
        if stop_distance <= 0:
            return None
        rr = abs(entry - tp1) / stop_distance
        if rr < self._config.min_risk_reward:
            return None

        log.info("[%s] SEÑAL RSI+EMA20 %s %s — RSI=%.1f EMA20=%.5f R:R=%.1f",
                 self._config.id, direction, instrument, rsi_val, ema20, rr)

        return ForexSignal(
            instrument=instrument, strategy_id=self._config.id, direction=direction,
            pattern_type=f"RSI_EMA20_{direction}", entry_price=entry,
            stop_price=stop, tp1_price=tp1, tp2_price=None,
            risk_reward_ratio=rr, confidence=0.55,
            market_state_h1=None, market_state_h4=None,
            filter_result=FilterResult(passed=True, passed_filters=[f"rsi_{rsi_val:.0f}", "ema20_zone"], failed_filters=[], total_filters=2),
            pullback_result=PullbackResult(is_valid=True, retrace_pct=0, distance_to_ema20=dist, distance_to_ema20_atr=dist / atr_val),
            entry_candle=current, entry_timeframe=self._config.entry_timeframe,
        )

    def _passes_rules(self, signal: ForexSignal) -> bool:
        from datetime import datetime, timezone
        for rule in self._rules:
            cond = rule.condition_json or {}
            if rule.rule_type == "time_filter" and datetime.now(timezone.utc).hour in cond.get("forbidden_hours", []):
                return False
            if rule.rule_type == "pattern_filter" and signal.pattern_type in cond.get("forbidden_patterns", []):
                return False
            if rule.rule_type == "condition_filter" and signal.confidence < cond.get("min_confidence", 0):
                return False
        return True
