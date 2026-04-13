"""Motor de señales S6/S7 — Pullback EMA20 en M5.

Versión simplificada de S1/S2 que opera en M5 para mayor frecuencia.
S6 = LONG only, S7 = SHORT only (determinado por config.direction).

Condiciones de entrada (3):
1. EMA20 slope confirma dirección (UP para LONG, DOWN para SHORT)
2. Precio dentro de 0.5 ATR de EMA20 (zona de pullback)
3. Vela de entrada confirma dirección (cuerpo > 30% del rango)

Salidas:
- SL: 1.5 × ATR(14)
- TP: 3.0 × ATR(14) → R:R = 2.0
"""

from __future__ import annotations

import logging

from app.broker.models import Candle
from app.forex.instruments import get_buffer_price
from app.signals.context_filters import FilterResult
from app.signals.indicators import atr, ema, ema_series
from app.signals.pullback_detector import PullbackResult
from app.signals.rule_engine import ForexSignal, ImprovementRuleCheck
from app.strategies.registry import StrategyConfig

log = logging.getLogger(__name__)

SL_ATR_MULT = 1.5
TP_ATR_MULT = 3.0
EMA_ZONE_ATR = 0.5
MIN_BODY_PCT = 0.30
SLOPE_LOOKBACK = 5


class PullbackEMA20M5Generator:
    """Genera señales S6/S7: pullback a EMA20 en M5."""

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
        atr_val = atr(candles, 14)
        if atr_val <= 0:
            return None

        # EMA20 slope
        ema_prev = ema(closes[:-SLOPE_LOOKBACK], 20)
        slope_up = ema20 > ema_prev
        slope_down = ema20 < ema_prev

        # Dirección basada en config
        direction = self._config.direction
        if direction == "LONG" and not slope_up:
            return None
        if direction == "SHORT" and not slope_down:
            return None
        if direction == "BOTH":
            if slope_up:
                direction = "LONG"
            elif slope_down:
                direction = "SHORT"
            else:
                return None

        # Precio en zona de EMA20 (dentro de 0.5 ATR)
        dist = abs(current.close - ema20)
        if dist > EMA_ZONE_ATR * atr_val:
            return None

        # Calidad de vela
        rng = current.high - current.low
        if rng <= 0:
            return None
        body_pct = abs(current.close - current.open) / rng
        if body_pct < MIN_BODY_PCT:
            return None

        # Confirmar dirección de la vela
        if direction == "LONG" and current.close <= current.open:
            return None
        if direction == "SHORT" and current.close >= current.open:
            return None

        buffer = get_buffer_price(instrument)
        if direction == "LONG":
            entry = current.close + buffer
            stop = entry - SL_ATR_MULT * atr_val
            tp1 = entry + TP_ATR_MULT * atr_val
        else:
            entry = current.close - buffer
            stop = entry + SL_ATR_MULT * atr_val
            tp1 = entry - TP_ATR_MULT * atr_val

        stop_distance = abs(entry - stop)
        if stop_distance <= 0:
            return None
        rr = abs(entry - tp1) / stop_distance
        if rr < self._config.min_risk_reward:
            return None

        log.info(
            "[%s] SEÑAL PULLBACK M5 %s %s — EMA20=%.5f dist=%.2f ATR entry=%.5f R:R=%.1f",
            self._config.id, direction, instrument, ema20, dist / atr_val, entry, rr,
        )

        return ForexSignal(
            instrument=instrument, strategy_id=self._config.id, direction=direction,
            pattern_type=f"PULLBACK_M5_{direction}", entry_price=entry,
            stop_price=stop, tp1_price=tp1, tp2_price=None,
            risk_reward_ratio=rr, confidence=0.55,
            market_state_h1=None, market_state_h4=None,
            filter_result=FilterResult(passed=True, passed_filters=["ema20_pullback_m5"], failed_filters=[], total_filters=1),
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
            if rule.rule_type == "condition_filter":
                if signal.confidence < cond.get("min_confidence", 0):
                    return False
                if signal.instrument in cond.get("forbidden_instruments", []):
                    return False
            if rule.rule_type == "candle_quality_filter" and signal.entry_candle:
                c = signal.entry_candle
                rng = c.high - c.low
                if rng > 0 and abs(c.close - c.open) / rng < cond.get("min_body_pct", 0):
                    return False
        return True
