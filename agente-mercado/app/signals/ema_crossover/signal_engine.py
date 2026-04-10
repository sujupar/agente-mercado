"""Motor de señales S3 — Cruce EMA9/EMA21 en M5.

Estrategia de ALTO VOLUMEN diseñada para generar 15-25 trades/día.
No necesita ser rentable desde el día 1 — su objetivo es generar
suficientes trades para que el motor de mejora aprenda y elimine errores.

Reglas:
- COMPRA: EMA9 cruza por encima de EMA21, cierre confirma
- VENTA: EMA9 cruza por debajo de EMA21, cierre confirma
- SL: 1.5 × ATR(14)
- TP: 2.0 × ATR(14)
"""

from __future__ import annotations

import logging

from app.broker.models import Candle
from app.forex.instruments import get_buffer_price
from app.signals.context_filters import FilterResult
from app.signals.indicators import atr, ema_series
from app.signals.pullback_detector import PullbackResult
from app.signals.rule_engine import ForexSignal, ImprovementRuleCheck
from app.strategies.registry import StrategyConfig

log = logging.getLogger(__name__)

# Parámetros del cruce
EMA_FAST = 9
EMA_SLOW = 21
SL_ATR_MULT = 1.5
TP_ATR_MULT = 2.0


class EMACrossoverGenerator:
    """Genera señales S3 basadas en cruce de EMA9/EMA21."""

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
        """Busca cruces de EMA en todos los instrumentos."""
        signals: list[ForexSignal] = []

        for instrument, candles in candles_data.items():
            if instrument not in self._config.instruments:
                continue
            if len(candles) < EMA_SLOW + 5:
                continue

            signal = self._detect_crossover(instrument, candles)
            if signal:
                # Verificar reglas de mejora (filtros aprendidos)
                if self._passes_improvement_rules(signal):
                    signals.append(signal)

        return signals

    def _detect_crossover(
        self, instrument: str, candles: list[Candle],
    ) -> ForexSignal | None:
        """Detecta cruce de EMA9/EMA21 en la última vela."""
        closes = [c.close for c in candles]

        # Calcular series completas de EMA
        fast = ema_series(closes, EMA_FAST)
        slow = ema_series(closes, EMA_SLOW)

        # Necesitamos al menos 2 valores en ambas series para detectar cruce
        if len(fast) < 2 or len(slow) < 2:
            return None

        # Alinear las series (ema_series retorna desde el período N)
        # fast tiene len(closes) - EMA_FAST + 1 elementos
        # slow tiene len(closes) - EMA_SLOW + 1 elementos
        # Alineamos al final
        fast_curr = fast[-1]
        fast_prev = fast[-2]
        slow_curr = slow[-1]
        slow_prev = slow[-2]

        current_price = closes[-1]
        current_candle = candles[-1]

        # ATR para stops
        atr_value = atr(candles, 14)
        if atr_value <= 0:
            return None

        buffer = get_buffer_price(instrument)
        direction = None

        # Cruce alcista: EMA9 cruza por encima de EMA21
        if fast_prev <= slow_prev and fast_curr > slow_curr:
            # Confirmar: cierre por encima de EMA21
            if current_price > slow_curr:
                direction = "LONG"

        # Cruce bajista: EMA9 cruza por debajo de EMA21
        elif fast_prev >= slow_prev and fast_curr < slow_curr:
            # Confirmar: cierre por debajo de EMA21
            if current_price < slow_curr:
                direction = "SHORT"

        if direction is None:
            return None

        # Calcular entry, SL, TP
        if direction == "LONG":
            entry = current_price + buffer
            stop = entry - SL_ATR_MULT * atr_value
            tp1 = entry + TP_ATR_MULT * atr_value
        else:
            entry = current_price - buffer
            stop = entry + SL_ATR_MULT * atr_value
            tp1 = entry - TP_ATR_MULT * atr_value

        stop_distance = abs(entry - stop)
        if stop_distance <= 0:
            return None

        rr = abs(entry - tp1) / stop_distance
        if rr < self._config.min_risk_reward:
            return None

        log.info(
            "[%s] SEÑAL EMA CROSSOVER %s %s — EMA9=%.5f EMA21=%.5f entry=%.5f R:R=%.1f",
            self._config.id, direction, instrument,
            fast_curr, slow_curr, entry, rr,
        )

        return ForexSignal(
            instrument=instrument,
            strategy_id=self._config.id,
            direction=direction,
            pattern_type=f"EMA_CROSS_{direction}",
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
                passed_filters=["ema_crossover"],
                failed_filters=[],
                total_filters=1,
            ),
            pullback_result=PullbackResult(
                is_valid=True, retrace_pct=0,
                distance_to_ema20=0, distance_to_ema20_atr=0,
            ),
            entry_candle=current_candle,
            entry_timeframe=self._config.entry_timeframe,
        )

    def _passes_improvement_rules(self, signal: ForexSignal) -> bool:
        """Verifica reglas de mejora aprendidas (mismo sistema que S1/S2)."""
        from datetime import datetime, timezone

        for rule in self._rules:
            condition = rule.condition_json
            if not condition:
                continue

            if rule.rule_type == "time_filter":
                forbidden_hours = condition.get("forbidden_hours", [])
                current_hour = datetime.now(timezone.utc).hour
                if current_hour in forbidden_hours:
                    return False

            elif rule.rule_type == "pattern_filter":
                forbidden_patterns = condition.get("forbidden_patterns", [])
                if signal.pattern_type in forbidden_patterns:
                    return False

            elif rule.rule_type == "condition_filter":
                min_confidence = condition.get("min_confidence", 0)
                if signal.confidence < min_confidence:
                    return False
                forbidden_instruments = condition.get("forbidden_instruments", [])
                if signal.instrument in forbidden_instruments:
                    return False

            elif rule.rule_type == "session_filter":
                forbidden_sessions = condition.get("forbidden_sessions", [])
                from app.forex.sessions import get_current_session
                if get_current_session() in forbidden_sessions:
                    return False

            elif rule.rule_type == "candle_quality_filter":
                if signal.entry_candle:
                    c = signal.entry_candle
                    rng = c.high - c.low
                    if rng > 0:
                        body_pct = abs(c.close - c.open) / rng
                        min_body = condition.get("min_body_pct", 0)
                        if body_pct < min_body:
                            return False

        return True
