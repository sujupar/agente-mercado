"""Motor de señales S10 — Momentum Breakout.

Condiciones (3):
1. Precio cierra > máximo de 20 períodos (LONG) o < mínimo (SHORT)
2. EMA20 slope confirma dirección
3. Breakout candle con cuerpo > 40% (momentum real, no mecha)

SL: lado opuesto del rango 20 períodos
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

LOOKBACK = 20
MIN_BODY_PCT = 0.40


class MomentumBreakoutGenerator:
    def __init__(self, config: StrategyConfig, improvement_rules: list[ImprovementRuleCheck] | None = None) -> None:
        self._config = config
        self._rules = improvement_rules or []

    def scan_entries(self, candles_data: dict[str, list[Candle]]) -> list[ForexSignal]:
        signals: list[ForexSignal] = []
        for instrument, candles in candles_data.items():
            if instrument not in self._config.instruments:
                continue
            if len(candles) < LOOKBACK + 5:
                continue
            signal = self._detect(instrument, candles)
            if signal and self._passes_rules(signal):
                signals.append(signal)
        return signals

    def _detect(self, instrument: str, candles: list[Candle]) -> ForexSignal | None:
        closes = [c.close for c in candles]
        current = candles[-1]

        # Rango de 20 períodos (excluyendo la vela actual)
        lookback_candles = candles[-(LOOKBACK + 1):-1]
        high_20 = max(c.high for c in lookback_candles)
        low_20 = min(c.low for c in lookback_candles)

        ema20 = ema(closes, 20)
        ema20_prev = ema(closes[:-5], 20)
        atr_val = atr(candles, 14)
        if atr_val <= 0:
            return None

        # Calidad de vela (cuerpo fuerte = momentum real)
        rng = current.high - current.low
        if rng <= 0:
            return None
        body_pct = abs(current.close - current.open) / rng
        if body_pct < MIN_BODY_PCT:
            return None

        direction = None
        buffer = get_buffer_price(instrument)

        # Breakout alcista: cierre > máximo 20
        if current.close > high_20 and ema20 > ema20_prev:
            direction = "LONG"
            entry = current.close + buffer
            stop = low_20 - buffer
            stop_distance = entry - stop
            tp1 = entry + stop_distance * 1.5

        # Breakout bajista: cierre < mínimo 20
        elif current.close < low_20 and ema20 < ema20_prev:
            direction = "SHORT"
            entry = current.close - buffer
            stop = high_20 + buffer
            stop_distance = stop - entry
            tp1 = entry - stop_distance * 1.5

        if direction is None:
            return None

        stop_distance = abs(entry - stop)
        if stop_distance <= 0:
            return None
        rr = abs(entry - tp1) / stop_distance
        if rr < self._config.min_risk_reward:
            return None

        log.info("[%s] SEÑAL MOMENTUM %s %s — high20=%.5f low20=%.5f entry=%.5f R:R=%.1f",
                 self._config.id, direction, instrument, high_20, low_20, entry, rr)

        return ForexSignal(
            instrument=instrument, strategy_id=self._config.id, direction=direction,
            pattern_type=f"MOMENTUM_BREAKOUT_{direction}", entry_price=entry,
            stop_price=stop, tp1_price=tp1, tp2_price=None,
            risk_reward_ratio=rr, confidence=0.55,
            market_state_h1=None, market_state_h4=None,
            filter_result=FilterResult(passed=True, passed_filters=["momentum_breakout"], failed_filters=[], total_filters=1),
            pullback_result=PullbackResult(is_valid=True, retrace_pct=0, distance_to_ema20=0, distance_to_ema20_atr=0),
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
