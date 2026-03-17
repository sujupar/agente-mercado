"""Orquestador Forex — monitorea 4 pares fijos, ejecuta S1/S2.

Flujo:
1. Verificar sesión de trading (Londres/NY)
2. Verificar que mercado Forex está abierto
3. Para cada instrumento: fetch candles H1+H4 desde OANDA
4. Para cada estrategia habilitada: generar señales, calcular position size, ejecutar
5. Gestionar posiciones abiertas (break-even, parciales, trailing)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.broker.base import BrokerInterface
from app.broker.models import Candle
from app.config import settings
from app.db.database import async_session_factory
from app.db.models import AgentState, Bitacora, Signal, Trade
from app.forex.instruments import calculate_position_size, is_spread_acceptable
from app.forex.sessions import get_current_session, is_forex_market_open, is_trading_session
from app.learning.bitacora_engine import BitacoraEngine
from app.learning.improvement_engine import ImprovementEngine
from app.llm.gemini import GeminiClient
from app.notifications.telegram import TelegramNotifier
from app.signals.rule_engine import ForexSignal, ForexSignalGenerator, ImprovementRuleCheck
from app.strategies.registry import STRATEGIES

log = logging.getLogger(__name__)


class ForexOrchestrator:
    """Orquesta las estrategias S1/S2 sobre pares Forex fijos vía OANDA."""

    def __init__(self, broker: BrokerInterface) -> None:
        self._broker = broker
        self._llm = GeminiClient()
        self._notifier = TelegramNotifier()
        self._instruments = settings.instruments_list
        self._cycle_count = 0

    async def run_cycle(self) -> None:
        """Ciclo principal: analizar mercado → señales → trades."""
        cycle_start = datetime.now(timezone.utc)
        session_name = get_current_session()

        log.info(
            "=== Ciclo Forex #%d | Sesión: %s | %s ===",
            self._cycle_count + 1,
            session_name,
            cycle_start.strftime("%H:%M UTC"),
        )

        # Verificar que el mercado está abierto
        if not is_forex_market_open():
            log.info("Mercado Forex cerrado (fin de semana) — saltando ciclo")
            return

        # Verificar sesión de trading para nuevas entradas
        can_open_new = is_trading_session()

        try:
            async with async_session_factory() as session:
                # FASE 1: Fetch candles de todos los instrumentos
                instruments_data = await self._fetch_all_candles()

                if not instruments_data:
                    log.warning("Sin datos de candles — saltando ciclo")
                    return

                log.info(
                    "Datos obtenidos para %d instrumentos: %s",
                    len(instruments_data),
                    ", ".join(instruments_data.keys()),
                )

                # FASE 2: Gestionar posiciones abiertas (siempre, incluso fuera de sesión)
                await self._manage_positions(session)

                # FASE 3: Buscar nuevas señales (solo durante sesión de trading)
                if can_open_new:
                    await self._scan_for_signals(session, instruments_data)
                else:
                    log.info("Fuera de sesión de trading — solo gestión de posiciones")

                await session.commit()

            elapsed = (datetime.now(timezone.utc) - cycle_start).total_seconds()
            log.info(
                "=== Ciclo Forex completado en %.1fs | Sesión: %s ===",
                elapsed, session_name,
            )

        except Exception:
            log.exception("Error fatal en ciclo Forex")

        self._cycle_count += 1

    async def _fetch_all_candles(self) -> dict[str, dict[str, list[Candle]]]:
        """Fetch candles H1 y H4 para todos los instrumentos."""
        result: dict[str, dict[str, list[Candle]]] = {}

        for instrument in self._instruments:
            try:
                candles_h1 = await self._broker.get_candles(instrument, "H1", 250)
                candles_h4 = await self._broker.get_candles(instrument, "H4", 100)

                if candles_h1:
                    result[instrument] = {
                        "H1": candles_h1,
                        "H4": candles_h4,
                    }
            except Exception:
                log.exception("Error fetching candles para %s", instrument)

        return result

    async def _scan_for_signals(
        self,
        session: AsyncSession,
        instruments_data: dict[str, dict[str, list[Candle]]],
    ) -> None:
        """Escanea señales para cada estrategia habilitada."""
        total_trades = 0

        for strategy_id, config in STRATEGIES.items():
            if not config.enabled:
                continue

            try:
                # Cargar improvement rules
                improvement_engine = ImprovementEngine(session)
                active_rules = await improvement_engine.get_active_rules(strategy_id)
                rule_checks = [
                    ImprovementRuleCheck(
                        id=r.id,
                        rule_type=r.rule_type,
                        pattern_name=r.pattern_name,
                        condition_json=r.condition_json or {},
                        description=r.description,
                    )
                    for r in active_rules
                ]

                # Generar señales
                generator = ForexSignalGenerator(config, rule_checks)
                signals = generator.generate_signals(instruments_data)

                # Ejecutar cada señal
                for signal in signals:
                    traded = await self._execute_signal(session, signal, strategy_id)
                    if traded:
                        total_trades += 1

                # Verificar ciclo de mejora y aprendizaje
                await self._check_learning(session, strategy_id, improvement_engine)

            except Exception:
                log.exception("Error en estrategia %s", strategy_id)

        if total_trades > 0:
            log.info("Total trades ejecutados este ciclo: %d", total_trades)

    async def _execute_signal(
        self,
        session: AsyncSession,
        signal: ForexSignal,
        strategy_id: str,
    ) -> bool:
        """Ejecuta una señal: verifica riesgo, coloca orden en OANDA, registra en DB."""

        # 1. Obtener estado de la cuenta del broker
        try:
            account = await self._broker.get_account()
        except Exception:
            log.exception("Error obteniendo cuenta del broker")
            return False

        # 2. Verificar límites
        open_positions = await self._broker.get_positions()
        strategy_config = STRATEGIES[strategy_id]

        if len(open_positions) >= strategy_config.max_concurrent_positions:
            log.info(
                "[%s] Máximo de posiciones alcanzado (%d/%d)",
                strategy_id, len(open_positions), strategy_config.max_concurrent_positions,
            )
            return False

        # 3. Verificar spread
        try:
            price = await self._broker.get_price(signal.instrument)
            if not is_spread_acceptable(signal.instrument, price.spread):
                return False
        except Exception:
            log.exception("Error obteniendo precio de %s", signal.instrument)
            return False

        # 4. Calcular position size
        stop_distance = abs(signal.entry_price - signal.stop_price)
        units = calculate_position_size(
            instrument=signal.instrument,
            account_balance=account.balance,
            risk_pct=strategy_config.risk_per_trade_pct,
            stop_distance_price=stop_distance,
            current_price=price.mid,
        )

        if units <= 0:
            return False

        # Ajustar signo según dirección
        if signal.direction == "SHORT":
            units = -units

        # 5. Colocar orden en OANDA
        order_result = await self._broker.place_market_order(
            instrument=signal.instrument,
            units=units,
            stop_loss=signal.stop_price,
            take_profit=signal.tp1_price,
        )

        if not order_result.success:
            log.warning(
                "[%s] Orden rechazada para %s: %s",
                strategy_id, signal.instrument, order_result.error,
            )
            return False

        # 6. Registrar señal en DB
        db_signal = Signal(
            strategy_id=strategy_id,
            market_id=f"oanda:{signal.instrument}",
            symbol=signal.instrument,
            estimated_value=0,
            market_price=order_result.fill_price or signal.entry_price,
            deviation_pct=0,
            direction="BUY" if signal.direction == "LONG" else "SELL",
            confidence=signal.confidence,
            take_profit_pct=signal.risk_reward_ratio * stop_distance / signal.entry_price if signal.entry_price > 0 else 0,
            stop_loss_pct=stop_distance / signal.entry_price if signal.entry_price > 0 else 0,
            llm_model=f"rule:{signal.pattern_type}",
            llm_prompt_hash="",
            llm_response_summary=f"Patrón {signal.pattern_type} en {signal.instrument}",
            data_sources_used=["oanda_h1", "oanda_h4", signal.pattern_type],
        )
        session.add(db_signal)
        await session.flush()

        # 7. Registrar trade en DB
        risk_amount = account.balance * strategy_config.risk_per_trade_pct
        trade = Trade(
            strategy_id=strategy_id,
            signal_id=db_signal.id,
            market_id=f"oanda:{signal.instrument}",
            symbol=signal.instrument,
            instrument=signal.instrument,
            direction="BUY" if signal.direction == "LONG" else "SELL",
            size_usd=abs(units) * (order_result.fill_price or signal.entry_price),
            quantity=abs(units),
            entry_price=order_result.fill_price or signal.entry_price,
            take_profit_price=signal.tp1_price,
            stop_loss_price=signal.stop_price,
            initial_stop_price=signal.stop_price,
            original_size_usd=abs(units) * (order_result.fill_price or signal.entry_price),
            pattern_name=signal.pattern_type,
            broker_trade_id=order_result.trade_id,
            risk_amount_usd=risk_amount,
            risk_reward_ratio=signal.risk_reward_ratio,
            stop_distance_pips=stop_distance,
            timeframe_entry="H1",
            context_timeframe="H4",
            market_state_json=signal.market_state_h1.to_dict(),
            status="OPEN",
            is_simulation=settings.oanda_environment == "practice",
        )
        session.add(trade)
        await session.flush()

        # 8. Bitácora
        bitacora = Bitacora(
            trade_id=trade.id,
            strategy_id=strategy_id,
            symbol=signal.instrument,
            direction=trade.direction,
            entry_reasoning=(
                f"Patrón {signal.pattern_type} en pullback a EMA20. "
                f"R:R={signal.risk_reward_ratio:.1f}. "
                f"Tendencia H1: {signal.market_state_h1.trend_state}. "
                f"8/8 filtros de contexto pasados."
            ),
            market_context=signal.market_state_h1.to_dict(),
            entry_price=trade.entry_price,
            entry_time=datetime.now(timezone.utc),
        )
        session.add(bitacora)

        # 9. Actualizar AgentState
        state = await self._ensure_state(session, strategy_id)
        state.positions_open += 1
        state.trades_executed_total += 1
        state.last_trade_at = datetime.now(timezone.utc)
        state.last_cycle_at = datetime.now(timezone.utc)

        # Sync broker balance
        state.broker_balance = account.balance
        state.broker_equity = account.equity
        state.last_broker_sync_at = datetime.now(timezone.utc)

        log.info(
            "[%s] ✓ Trade ejecutado: %s %s %s | Entry=%.5f | SL=%.5f | TP=%.5f | R:R=%.1f | Units=%d",
            strategy_id,
            signal.direction,
            signal.instrument,
            signal.pattern_type,
            trade.entry_price,
            trade.stop_loss_price,
            trade.take_profit_price,
            signal.risk_reward_ratio,
            abs(units),
        )

        # Notificar por Telegram
        try:
            await self._notifier.send(
                f"📊 Trade {signal.direction} {signal.instrument}\n"
                f"Patrón: {signal.pattern_type}\n"
                f"Entry: {trade.entry_price:.5f}\n"
                f"SL: {trade.stop_loss_price:.5f}\n"
                f"TP: {trade.take_profit_price:.5f}\n"
                f"R:R: {signal.risk_reward_ratio:.1f}"
            )
        except Exception:
            pass  # No bloquear por fallo de notificación

        return True

    async def _manage_positions(self, session: AsyncSession) -> None:
        """Gestiona posiciones abiertas: break-even, parciales, trailing, sync."""
        try:
            broker_positions = await self._broker.get_positions()
        except Exception:
            log.exception("Error obteniendo posiciones del broker")
            return

        # Obtener trades abiertos de la DB
        result = await session.execute(
            select(Trade).where(Trade.status == "OPEN", Trade.broker_trade_id.isnot(None))
        )
        db_trades = {t.broker_trade_id: t for t in result.scalars().all()}

        # Reconciliar: posiciones en broker que ya cerraron
        broker_trade_ids = {p.trade_id for p in broker_positions}
        for broker_id, db_trade in db_trades.items():
            if broker_id not in broker_trade_ids:
                # Trade cerrado en broker (TP/SL hit) — sincronizar
                await self._sync_closed_trade(session, db_trade)

        # Para posiciones abiertas: gestionar break-even y trailing
        for position in broker_positions:
            if position.trade_id not in db_trades:
                log.warning(
                    "Posición %s en broker sin trade en DB — ignorando",
                    position.trade_id,
                )
                continue

            db_trade = db_trades[position.trade_id]
            await self._manage_single_position(session, db_trade, position)

    async def _manage_single_position(
        self,
        _session: AsyncSession,
        trade: Trade,
        position,
    ) -> None:
        """Gestiona una posición individual: break-even, parciales."""
        entry = trade.entry_price
        initial_stop = trade.initial_stop_price or trade.stop_loss_price
        stop_distance = abs(entry - initial_stop)

        if stop_distance <= 0:
            return

        # Break-even at 1R
        if trade.partial_exits == 0:
            current_price_vs_entry = (
                (position.unrealized_pnl > 0 and abs(position.unrealized_pnl) / abs(position.units) >= stop_distance)
                if position.units != 0 else False
            )

            if current_price_vs_entry and position.stop_loss != entry:
                # Mover stop a break-even
                result = await self._broker.modify_trade(
                    trade_id=position.trade_id,
                    stop_loss=entry,
                )
                if result.success:
                    trade.stop_loss_price = entry
                    log.info(
                        "[%s] Break-even activado para %s %s",
                        trade.strategy_id, trade.direction, trade.instrument,
                    )

    async def _sync_closed_trade(self, session: AsyncSession, trade: Trade) -> None:
        """Sincroniza un trade que fue cerrado en el broker."""
        trade.status = "CLOSED"
        trade.closed_at = datetime.now(timezone.utc)

        # Intentar obtener info del trade cerrado
        # (El P&L real viene del broker en la reconciliación diaria)
        log.info(
            "[%s] Trade %s %s cerrado por broker (TP/SL hit)",
            trade.strategy_id, trade.direction, trade.instrument,
        )

        # Actualizar AgentState
        state = await self._ensure_state(session, trade.strategy_id)
        state.positions_open = max(0, state.positions_open - 1)

    async def _check_learning(
        self,
        session: AsyncSession,
        strategy_id: str,
        improvement_engine: ImprovementEngine,
    ) -> None:
        """Verifica si hay ciclos de mejora o reportes pendientes."""
        from app.db.models import ImprovementCycle

        try:
            # Verificar ciclos de mejora pendientes
            result = await session.execute(
                select(ImprovementCycle).where(
                    ImprovementCycle.strategy_id == strategy_id,
                    ImprovementCycle.status == "analyzing",
                )
            )
            analyzing = result.scalar_one_or_none()
            if analyzing:
                await improvement_engine.analyze_cycle(strategy_id)

            # Verificar si toca reporte de aprendizaje
            engine = BitacoraEngine(session, self._llm)
            if await engine.should_generate_report(strategy_id):
                log.info("[%s] Generando reporte de aprendizaje...", strategy_id)
                await engine.generate_lessons_batch(strategy_id)
                await engine.generate_learning_report(strategy_id)
        except Exception:
            log.exception("[%s] Error en sistema de aprendizaje", strategy_id)

    async def _ensure_state(self, session: AsyncSession, strategy_id: str) -> AgentState:
        """Obtiene o crea AgentState para una estrategia."""
        result = await session.execute(
            select(AgentState).where(AgentState.strategy_id == strategy_id)
        )
        state = result.scalar_one_or_none()
        if not state:
            config = STRATEGIES.get(strategy_id)
            initial = config.initial_capital_usd if config else 100_000.0
            state = AgentState(
                strategy_id=strategy_id,
                mode="SIMULATION" if settings.oanda_environment == "practice" else "LIVE",
                capital_usd=initial,
                peak_capital_usd=initial,
            )
            session.add(state)
            await session.flush()
        return state

    async def close(self) -> None:
        """Libera recursos."""
        await self._broker.close()
        await self._llm.close()
        await self._notifier.close()
