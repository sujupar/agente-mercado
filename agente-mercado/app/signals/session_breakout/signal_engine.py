"""Motor de señales S5 — Ruptura del Rango de Apertura de Sesión en M5.

Cada sesión (Londres, Nueva York) forma un rango en los primeros 30 minutos.
Si el precio rompe ese rango, entramos en la dirección de la ruptura.

Reglas:
- Rango = Máximo/Mínimo de los primeros 30 min (6 velas M5)
- COMPRA: cierre > máximo del rango
- VENTA: cierre < mínimo del rango
- SL: lado opuesto del rango
- TP: 1.5× ancho del rango
- Cierre por tiempo al final de sesión
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.broker.models import Candle
from app.forex.instruments import get_buffer_price
from app.signals.context_filters import FilterResult
from app.signals.indicators import atr
from app.signals.pullback_detector import PullbackResult
from app.signals.rule_engine import ForexSignal, ImprovementRuleCheck
from app.strategies.registry import StrategyConfig

log = logging.getLogger(__name__)

# Sesiones y sus horarios de apertura (UTC)
SESSIONS = [
    {"name": "London", "range_start": 7, "range_end_min": 30, "session_end": 16},
    {"name": "New York", "range_start": 12, "range_end_min": 30, "session_end": 21},
]

MIN_RANGE_ATR_MULT = 0.5  # Rango mínimo = 0.5 × ATR
TP_RANGE_MULT = 1.5  # TP = 1.5× el ancho del rango


class SessionBreakoutGenerator:
    """Genera señales S5 basadas en ruptura del rango de apertura de sesión."""

    def __init__(
        self,
        config: StrategyConfig,
        improvement_rules: list[ImprovementRuleCheck] | None = None,
    ) -> None:
        self._config = config
        self._rules = improvement_rules or []
        # Rangos calculados hoy {session_name: (high, low, calculated)}
        self._session_ranges: dict[str, tuple[float, float]] = {}
        self._ranges_date: str = ""

    def scan_entries(
        self,
        candles_data: dict[str, list[Candle]],
    ) -> list[ForexSignal]:
        signals: list[ForexSignal] = []
        now = datetime.now(timezone.utc)

        for instrument, candles in candles_data.items():
            if instrument not in self._config.instruments:
                continue
            if len(candles) < 30:
                continue

            signal = self._check_breakout(instrument, candles, now)
            if signal and self._passes_improvement_rules(signal):
                signals.append(signal)

        return signals

    def _check_breakout(
        self, instrument: str, candles: list[Candle], now: datetime,
    ) -> ForexSignal | None:
        """Verifica si hay ruptura del rango de apertura de alguna sesión."""
        current = candles[-1]
        atr_value = atr(candles, 14)
        if atr_value <= 0:
            return None

        for session in SESSIONS:
            start_hour = session["range_start"]
            range_end_min = session["range_end_min"]
            session_end = session["session_end"]
            session_name = session["name"]

            # Solo operar después de que el rango se formó y antes del cierre
            if now.hour < start_hour or now.hour >= session_end:
                continue
            # El rango se forma en los primeros 30 min
            if now.hour == start_hour and now.minute < range_end_min:
                continue

            # Calcular rango de apertura usando velas históricas
            range_high, range_low = self._calculate_opening_range(
                candles, start_hour, range_end_min,
            )
            if range_high is None or range_low is None:
                continue

            range_width = range_high - range_low
            if range_width <= 0:
                continue

            # Filtro: rango debe ser al menos 0.5 × ATR
            if range_width < MIN_RANGE_ATR_MULT * atr_value:
                continue

            buffer = get_buffer_price(instrument)
            direction = None

            # Ruptura alcista
            if current.close > range_high:
                direction = "LONG"
                entry = current.close + buffer
                stop = range_low - buffer
                tp1 = entry + range_width * TP_RANGE_MULT

            # Ruptura bajista
            elif current.close < range_low:
                direction = "SHORT"
                entry = current.close - buffer
                stop = range_high + buffer
                tp1 = entry - range_width * TP_RANGE_MULT

            if direction is None:
                continue

            stop_distance = abs(entry - stop)
            if stop_distance <= 0:
                continue

            rr = abs(entry - tp1) / stop_distance
            if rr < self._config.min_risk_reward:
                continue

            log.info(
                "[%s] SEÑAL SESSION BREAKOUT %s %s — %s range[%.5f-%.5f] entry=%.5f R:R=%.1f",
                self._config.id, direction, instrument,
                session_name, range_low, range_high, entry, rr,
            )

            return ForexSignal(
                instrument=instrument,
                strategy_id=self._config.id,
                direction=direction,
                pattern_type=f"SESSION_BREAKOUT_{session_name.upper()}_{direction}",
                entry_price=entry,
                stop_price=stop,
                tp1_price=tp1,
                tp2_price=None,
                risk_reward_ratio=rr,
                confidence=0.55,
                market_state_h1=None,
                market_state_h4=None,
                filter_result=FilterResult(
                    passed=True,
                    passed_filters=[f"session_range_{session_name.lower()}"],
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

        return None

    def _calculate_opening_range(
        self,
        candles: list[Candle],
        start_hour: int,
        range_minutes: int,
    ) -> tuple[float | None, float | None]:
        """Calcula el rango (max, min) de los primeros N minutos de la sesión de hoy."""
        today = datetime.now(timezone.utc).date()
        range_candles = []

        for c in candles:
            if c.timestamp.date() != today:
                continue
            if c.timestamp.hour == start_hour and c.timestamp.minute < range_minutes:
                range_candles.append(c)

        if not range_candles:
            return None, None

        range_high = max(c.high for c in range_candles)
        range_low = min(c.low for c in range_candles)
        return range_high, range_low

    def _passes_improvement_rules(self, signal: ForexSignal) -> bool:
        """Misma lógica de filtros que las otras estrategias."""
        from datetime import datetime as dt, timezone as tz

        for rule in self._rules:
            condition = rule.condition_json
            if not condition:
                continue

            if rule.rule_type == "time_filter":
                if dt.now(tz.utc).hour in condition.get("forbidden_hours", []):
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

        return True
