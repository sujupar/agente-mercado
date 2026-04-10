"""Motor de señales S4 — Reversión a la Media con Bandas de Bollinger en M5.

Lógica OPUESTA a S1/S2 (que son tendenciales). Esta estrategia compra
cuando el precio toca la banda inferior y vende cuando toca la superior.

Reglas:
- COMPRA: precio perfora banda inferior BB(20,2) y cierra dentro + cuerpo >30%
- VENTA: precio perfora banda superior BB(20,2) y cierra dentro + cuerpo >30%
- SL: extremo de banda + 0.5 × ATR(14)
- TP: banda media (SMA20) — volviendo a la media
"""

from __future__ import annotations

import logging

from app.broker.models import Candle
from app.forex.instruments import get_buffer_price
from app.signals.context_filters import FilterResult
from app.signals.indicators import atr, bollinger_bands
from app.signals.pullback_detector import PullbackResult
from app.signals.rule_engine import ForexSignal, ImprovementRuleCheck
from app.strategies.registry import StrategyConfig

log = logging.getLogger(__name__)

BB_PERIOD = 20
BB_STD = 2.0
SL_ATR_MULT = 0.5
MIN_BODY_PCT = 0.30


class BollingerMeanReversionGenerator:
    """Genera señales S4 basadas en toques de Bandas de Bollinger."""

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
        signals: list[ForexSignal] = []

        for instrument, candles in candles_data.items():
            if instrument not in self._config.instruments:
                continue
            if len(candles) < BB_PERIOD + 5:
                continue

            signal = self._detect_band_touch(instrument, candles)
            if signal and self._passes_improvement_rules(signal):
                signals.append(signal)

        return signals

    def _detect_band_touch(
        self, instrument: str, candles: list[Candle],
    ) -> ForexSignal | None:
        closes = [c.close for c in candles]
        current = candles[-1]
        prev = candles[-2]

        # Bandas de Bollinger actuales
        upper, middle, lower = bollinger_bands(closes, BB_PERIOD, BB_STD)

        # ATR para SL
        atr_value = atr(candles, 14)
        if atr_value <= 0:
            return None

        # Calidad de vela: cuerpo > 30% del rango
        rng = current.high - current.low
        if rng <= 0:
            return None
        body_pct = abs(current.close - current.open) / rng
        if body_pct < MIN_BODY_PCT:
            return None

        buffer = get_buffer_price(instrument)
        direction = None

        # COMPRA: precio perforó banda inferior y cerró dentro
        if current.low <= lower and current.close > lower:
            # Confirmar: vela anterior también estaba en/más allá de la banda
            if prev.low <= lower or prev.close <= lower:
                direction = "LONG"

        # VENTA: precio perforó banda superior y cerró dentro
        elif current.high >= upper and current.close < upper:
            if prev.high >= upper or prev.close >= upper:
                direction = "SHORT"

        if direction is None:
            return None

        # Entry, SL, TP
        if direction == "LONG":
            entry = current.close + buffer
            stop = lower - SL_ATR_MULT * atr_value
            tp1 = middle  # Reversión a la media
        else:
            entry = current.close - buffer
            stop = upper + SL_ATR_MULT * atr_value
            tp1 = middle

        stop_distance = abs(entry - stop)
        if stop_distance <= 0:
            return None

        rr = abs(entry - tp1) / stop_distance
        if rr < self._config.min_risk_reward:
            return None

        log.info(
            "[%s] SEÑAL BOLLINGER %s %s — BB[%.5f-%.5f-%.5f] entry=%.5f R:R=%.1f",
            self._config.id, direction, instrument,
            lower, middle, upper, entry, rr,
        )

        return ForexSignal(
            instrument=instrument,
            strategy_id=self._config.id,
            direction=direction,
            pattern_type=f"BB_REVERSION_{direction}",
            entry_price=entry,
            stop_price=stop,
            tp1_price=tp1,
            tp2_price=None,
            risk_reward_ratio=rr,
            confidence=0.5,
            market_state_h1=None,
            market_state_h4=None,
            filter_result=FilterResult(
                passed=True,
                passed_filters=["bollinger_touch"],
                failed_filters=[],
                total_filters=1,
            ),
            pullback_result=PullbackResult(
                is_valid=True, retrace_pct=0,
                distance_to_ema20=0, distance_to_ema20_atr=0,
            ),
            entry_candle=current,
            entry_timeframe=self._config.entry_timeframe,
        )

    def _passes_improvement_rules(self, signal: ForexSignal) -> bool:
        """Misma lógica de filtros que las otras estrategias."""
        from datetime import datetime, timezone

        for rule in self._rules:
            condition = rule.condition_json
            if not condition:
                continue

            if rule.rule_type == "time_filter":
                if datetime.now(timezone.utc).hour in condition.get("forbidden_hours", []):
                    return False
            elif rule.rule_type == "pattern_filter":
                if signal.pattern_type in condition.get("forbidden_patterns", []):
                    return False
            elif rule.rule_type == "condition_filter":
                if signal.confidence < condition.get("min_confidence", 0):
                    return False
                if signal.instrument in condition.get("forbidden_instruments", []):
                    return False
            elif rule.rule_type == "session_filter":
                from app.forex.sessions import get_current_session
                if get_current_session() in condition.get("forbidden_sessions", []):
                    return False
            elif rule.rule_type == "candle_quality_filter":
                if signal.entry_candle:
                    c = signal.entry_candle
                    rng = c.high - c.low
                    if rng > 0:
                        if abs(c.close - c.open) / rng < condition.get("min_body_pct", 0):
                            return False

        return True
