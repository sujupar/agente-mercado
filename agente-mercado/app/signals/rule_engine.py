"""Pipeline de señales Forex — Oliver Vélez S1/S2.

Flujo por instrumento:
1. Fetch candles H1 (250) + H4 (100) desde OANDA
2. Construir MarketState H1 y H4
3. Correr 8 filtros de contexto → si alguno falla, skip
4. Detectar pullback a EMA20
5. Si hay pullback, buscar patrón de entrada en últimas 3 velas H1
6. Si hay patrón, calcular stop y verificar R:R >= 2:1
7. Aplicar filtro de improvement rules
8. Generar señal
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.broker.models import Candle
from app.forex.instruments import get_buffer_price
from app.signals.context_filters import ContextFilterEngine, FilterResult
from app.signals.entry_patterns import EntryPatternDetector, PatternResult
from app.signals.market_state import MarketState, MarketStateAnalyzer
from app.signals.pullback_detector import PullbackDetector, PullbackResult
from app.strategies.registry import StrategyConfig

log = logging.getLogger(__name__)


@dataclass
class ForexSignal:
    """Señal de trading generada por el pipeline."""

    instrument: str
    strategy_id: str
    direction: str  # "LONG" | "SHORT"
    pattern_type: str
    entry_price: float
    stop_price: float
    tp1_price: float
    tp2_price: float | None
    risk_reward_ratio: float
    confidence: float

    # Context snapshot
    market_state_h1: MarketState
    market_state_h4: MarketState | None
    filter_result: FilterResult
    pullback_result: PullbackResult

    created_at: datetime = None  # type: ignore

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


@dataclass
class ImprovementRuleCheck:
    """Regla de mejora para filtrar señales (permanente e irrevocable)."""

    id: int
    rule_type: str
    pattern_name: str
    condition_json: dict
    description: str


class ForexSignalGenerator:
    """Genera señales S1/S2 según el Plan de Trading de Oliver Vélez.

    Reemplaza al antiguo RuleBasedSignalGenerator.
    """

    def __init__(
        self,
        config: StrategyConfig,
        improvement_rules: list[ImprovementRuleCheck] | None = None,
    ) -> None:
        self._config = config
        self._rules = improvement_rules or []
        self._state_analyzer = MarketStateAnalyzer()
        self._filter_engine = ContextFilterEngine()
        self._pattern_detector = EntryPatternDetector()
        self._pullback_detector = PullbackDetector()

    def generate_signals(
        self,
        instruments_data: dict[str, dict[str, list[Candle]]],
    ) -> list[ForexSignal]:
        """Genera señales para todos los instrumentos.

        Args:
            instruments_data: {
                "EUR_USD": {
                    "H1": [Candle, ...],
                    "H4": [Candle, ...],
                },
                ...
            }

        Returns:
            Lista de ForexSignal aprobadas.
        """
        direction = self._config.direction
        all_signals: list[ForexSignal] = []

        for instrument, timeframes in instruments_data.items():
            candles_h1 = timeframes.get("H1", [])
            candles_h4 = timeframes.get("H4", [])

            signal = self._analyze_instrument(
                instrument, candles_h1, candles_h4, direction,
            )
            if signal:
                all_signals.append(signal)

        if all_signals:
            log.info(
                "[%s] %d señales generadas: %s",
                self._config.id,
                len(all_signals),
                ", ".join(f"{s.instrument} {s.pattern_type}" for s in all_signals),
            )

        return all_signals

    def _analyze_instrument(
        self,
        instrument: str,
        candles_h1: list[Candle],
        candles_h4: list[Candle],
        direction: str,
    ) -> ForexSignal | None:
        """Analiza un instrumento y genera señal si cumple todas las condiciones."""

        # 1. Construir MarketState
        state_h1 = self._state_analyzer.analyze(instrument, "H1", candles_h1)
        if state_h1 is None:
            return None

        state_h4 = None
        if candles_h4:
            state_h4 = self._state_analyzer.analyze(instrument, "H4", candles_h4)

        # 2. Filtros de contexto (8 obligatorios)
        filter_result = self._filter_engine.check_all_filters(state_h1, state_h4, direction)
        if not filter_result.passed:
            return None

        # 3. Detectar pullback a EMA20
        pullback = self._pullback_detector.detect(state_h1, direction)
        if not pullback.is_valid:
            return None

        # 4. Buscar patrón de entrada en últimas velas H1
        recent_candles = candles_h1[-5:]  # Últimas 5 velas para análisis
        patterns = self._pattern_detector.detect_all(recent_candles, direction)
        if not patterns:
            return None

        # Tomar el patrón con mayor confianza
        best_pattern = max(patterns, key=lambda p: p.confidence)

        # 5. Calcular entry, stop y TP con buffer
        buffer = get_buffer_price(instrument)
        signal = self._build_signal(
            instrument, direction, best_pattern, state_h1, state_h4,
            filter_result, pullback, buffer,
        )

        if signal is None:
            return None

        # 6. Filtrar por improvement rules
        if not self._passes_improvement_rules(signal):
            log.info(
                "[%s] Señal %s %s rechazada por regla de mejora",
                self._config.id, direction, instrument,
            )
            return None

        return signal

    def _build_signal(
        self,
        instrument: str,
        direction: str,
        pattern: PatternResult,
        state_h1: MarketState,
        state_h4: MarketState | None,
        filter_result: FilterResult,
        pullback: PullbackResult,
        buffer: float,
    ) -> ForexSignal | None:
        """Construye la señal con cálculos de entry/stop/TP y validación R:R."""

        if direction == "LONG":
            entry = pattern.pattern_high + buffer
            stop = pattern.pattern_low - buffer
            stop_distance = entry - stop

            if stop_distance <= 0:
                return None

            # TP1 = 2R (mínimo)
            tp1 = entry + (stop_distance * self._config.min_risk_reward)
            # TP2 = swing high anterior o 3R
            tp2 = max(state_h1.last_swing_high, entry + stop_distance * 3)

        else:  # SHORT
            entry = pattern.pattern_low - buffer
            stop = pattern.pattern_high + buffer
            stop_distance = stop - entry

            if stop_distance <= 0:
                return None

            tp1 = entry - (stop_distance * self._config.min_risk_reward)
            tp2 = min(state_h1.last_swing_low, entry - stop_distance * 3)

        # Verificar R:R
        rr = (abs(entry - tp1)) / stop_distance if stop_distance > 0 else 0
        if rr < self._config.min_risk_reward:
            log.debug(
                "R:R insuficiente para %s: %.2f (mín: %.1f)",
                instrument, rr, self._config.min_risk_reward,
            )
            return None

        return ForexSignal(
            instrument=instrument,
            strategy_id=self._config.id,
            direction=direction,
            pattern_type=pattern.pattern_type,
            entry_price=entry,
            stop_price=stop,
            tp1_price=tp1,
            tp2_price=tp2,
            risk_reward_ratio=rr,
            confidence=pattern.confidence,
            market_state_h1=state_h1,
            market_state_h4=state_h4,
            filter_result=filter_result,
            pullback_result=pullback,
        )

    def _passes_improvement_rules(self, signal: ForexSignal) -> bool:
        """Verifica que la señal no viole reglas de mejora permanentes."""
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

        return True
