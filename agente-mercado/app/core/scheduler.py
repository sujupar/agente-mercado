"""Scheduler Forex — APScheduler para el orquestador + sync de posiciones."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_orchestrator = None
_broker = None


def _get_broker():
    """Crea el broker singleton según la configuración."""
    global _broker
    if _broker is not None:
        return _broker

    provider = settings.broker_provider.lower()

    if provider == "capital":
        from app.broker.capital import CapitalBroker
        if settings.capital_api_key and settings.capital_identifier:
            _broker = CapitalBroker(
                api_key=settings.capital_api_key,
                identifier=settings.capital_identifier,
                password=settings.capital_password,
                environment=settings.capital_environment,
            )
            log.info(
                "Broker Capital.com inicializado: env=%s",
                settings.capital_environment,
            )
        else:
            log.warning(
                "Capital.com no configurado (falta api_key o identifier) — "
                "el orquestador no podrá operar"
            )
    elif provider == "oanda":
        from app.broker.oanda import OANDABroker
        if settings.oanda_account_id and settings.oanda_access_token:
            _broker = OANDABroker(
                account_id=settings.oanda_account_id,
                access_token=settings.oanda_access_token,
                environment=settings.oanda_environment,
            )
            log.info(
                "Broker OANDA inicializado: env=%s",
                settings.oanda_environment,
            )
        else:
            log.warning(
                "OANDA no configurado (falta account_id o access_token) — "
                "el orquestador no podrá operar"
            )
    else:
        log.error("Broker provider desconocido: %s (usar 'capital' o 'oanda')", provider)

    return _broker


async def _run_orchestrator_cycle():
    """Ejecuta un ciclo del orquestador Forex."""
    global _orchestrator
    broker = _get_broker()
    if broker is None:
        return

    if _orchestrator is None:
        from app.core.orchestrator import ForexOrchestrator
        _orchestrator = ForexOrchestrator(broker)

    try:
        await _orchestrator.run_cycle()
    except Exception:
        log.exception("Error en ciclo del orquestador Forex")


async def _run_position_sync():
    """Sincroniza posiciones con el broker."""
    broker = _get_broker()
    if broker is None:
        return

    try:
        from app.db.database import async_session_factory
        from app.core.orchestrator import ForexOrchestrator

        global _orchestrator
        if _orchestrator is None:
            _orchestrator = ForexOrchestrator(broker)

        async with async_session_factory() as session:
            await _orchestrator._manage_positions(session)
            await session.commit()
    except Exception:
        log.exception("Error en sincronización de posiciones")


async def start_scheduler() -> None:
    global _scheduler
    _scheduler = AsyncIOScheduler()

    # Job 1: Ciclo Forex — cada N min
    cycle_minutes = max(settings.cycle_interval_minutes, 5)
    _scheduler.add_job(
        _run_orchestrator_cycle,
        trigger=IntervalTrigger(minutes=cycle_minutes),
        id="orchestrator_cycle",
        name="Ciclo Forex (señales + trades)",
        replace_existing=True,
        max_instances=1,
    )

    # Job 2: Sync de posiciones — cada 30 segundos
    _scheduler.add_job(
        _run_position_sync,
        trigger=IntervalTrigger(seconds=30),
        id="position_sync",
        name="Sincronización posiciones broker",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    log.info(
        "Scheduler Forex iniciado: broker=%s, ciclo=%dmin, sync=30seg",
        settings.broker_provider,
        cycle_minutes,
    )


async def stop_scheduler() -> None:
    global _scheduler, _orchestrator, _broker
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("Scheduler detenido")
    if _orchestrator:
        await _orchestrator.close()
        _orchestrator = None
    if _broker:
        await _broker.close()
        _broker = None


async def trigger_manual_cycle() -> None:
    """Fuerza un ciclo manual fuera del scheduler."""
    await _run_orchestrator_cycle()
