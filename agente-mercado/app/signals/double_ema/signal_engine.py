"""Motor de señales S8 — Double EMA Pullback.

Condiciones (3):
1. EMA20 > EMA50 para LONG (o < para SHORT) — EMAs alineadas
2. Ambas EMAs con slope en la misma dirección
3. Precio toca zona EMA20 (dentro de 0.5 ATR)

SL: debajo de EMA50 (LONG) o encima (SHORT)
TP: 1.5× stop distance
"""

from __future__ import annotations

import logging

from app.broker.models import Candle
from app.forex.instruments import get_buffer_price
from app.signals.context_filters import FilterResult
from app.signals.indicators import atr, ema
from app.signals.pullback_detector import PullbackResult
from app.signals.rule_engine import ForexSignal, ImprovementRuleCheck
from app.strategies.registry import StrategyConfig

log = logging.getLogger(__name__)


class DoubleEMAPullbackGenerator:
    def __init__(self, config: StrategyConfig, improvement_rules: list[ImprovementRuleCheck] | None = None) -> None:
        self._config = config
        self._rules = improvement_rules or []

    def scan_entries(self, candles_data: dict[str, list[Candle]]) -> list[ForexSignal]:
        signals: list[ForexSignal] = []
        for instrument, candles in candles_data.items():
            if instrument not in self._config.instruments:
                continue
            if len(candles) < 55:
                continue
            signal = self._detect(instrument, candles)
            if signal and self._passes_rules(signal):
                signals.append(signal)
        return signals

    def _detect(self, instrument: str, candles: list[Candle]) -> ForexSignal | None:
        closes = [c.close for c in candles]
        current = candles[-1]
        ema20 = ema(closes, 20)
        ema50 = ema(closes, 50)
        ema20_prev = ema(closes[:-5], 20)
        ema50_prev = ema(closes[:-5], 50)
        atr_val = atr(candles, 14)
        if atr_val <= 0:
            return None

        # 1. EMAs alineadas
        ema20_above = ema20 > ema50
        ema20_below = ema20 < ema50

        # 2. Slopes en misma dirección
        ema20_rising = ema20 > ema20_prev
        ema50_rising = ema50 > ema50_prev
        ema20_falling = ema20 < ema20_prev
        ema50_falling = ema50 < ema50_prev

        direction = None
        if ema20_above and ema20_rising and ema50_rising:
            direction = "LONG"
        elif ema20_below and ema20_falling and ema50_falling:
            direction = "SHORT"

        if direction is None:
            return None

        # 3. Precio en zona EMA20
        dist = abs(current.close - ema20)
        if dist > 0.5 * atr_val:
            return None

        buffer = get_buffer_price(instrument)
        if direction == "LONG":
            entry = current.close + buffer
            stop = ema50 - 0.3 * atr_val
            tp1 = entry + abs(entry - stop) * 1.5
        else:
            entry = current.close - buffer
            stop = ema50 + 0.3 * atr_val
            tp1 = entry - abs(stop - entry) * 1.5

        stop_distance = abs(entry - stop)
        if stop_distance <= 0:
            return None
        rr = abs(entry - tp1) / stop_distance
        if rr < self._config.min_risk_reward:
            return None

        log.info("[%s] SEÑAL DOUBLE EMA %s %s — EMA20=%.5f EMA50=%.5f R:R=%.1f",
                 self._config.id, direction, instrument, ema20, ema50, rr)

        return ForexSignal(
            instrument=instrument, strategy_id=self._config.id, direction=direction,
            pattern_type=f"DOUBLE_EMA_{direction}", entry_price=entry,
            stop_price=stop, tp1_price=tp1, tp2_price=None,
            risk_reward_ratio=rr, confidence=0.55,
            market_state_h1=None, market_state_h4=None,
            filter_result=FilterResult(passed=True, passed_filters=["double_ema"], failed_filters=[], total_filters=1),
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
