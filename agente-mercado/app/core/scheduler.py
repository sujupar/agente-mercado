"""Scheduler Forex — APScheduler para el orquestador + sync de posiciones."""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_orchestrator = None
_broker = None
_current_environment: str | None = None  # Cache del env actual (DEMO/LIVE)


async def get_current_environment() -> str:
    """Retorna el environment activo del broker (leído desde SystemConfig).

    Fallback: settings.capital_environment (env var).
    Cachea el resultado en _current_environment para performance.
    """
    global _current_environment
    if _current_environment is not None:
        return _current_environment

    try:
        from app.db.system_config import get_config
        env = await get_config(
            "broker.environment",
            default=settings.capital_environment,
        )
        _current_environment = (env or settings.capital_environment).upper()
    except Exception:
        log.exception("Error leyendo broker.environment — usando .env fallback")
        _current_environment = settings.capital_environment.upper()

    return _current_environment


def _get_broker():
    """Crea el broker singleton según la configuración.

    El environment se lee de SystemConfig si está disponible (leído
    previamente por get_current_environment y cacheado en _current_environment).
    Fallback a settings.capital_environment si no hay cache.
    """
    global _broker
    if _broker is not None:
        return _broker

    provider = settings.broker_provider.lower()

    if provider == "capital":
        from app.broker.capital import CapitalBroker
        if settings.capital_api_key and settings.capital_identifier:
            # Usa el env cacheado si existe, sino el del settings
            env = _current_environment or settings.capital_environment
            _broker = CapitalBroker(
                api_key=settings.capital_api_key,
                identifier=settings.capital_identifier,
                password=settings.capital_password,
                environment=env,
            )
            log.info("Broker Capital.com inicializado: env=%s", env)
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
            log.info("Broker OANDA inicializado: env=%s", settings.oanda_environment)
        else:
            log.warning(
                "OANDA no configurado (falta account_id o access_token) — "
                "el orquestador no podrá operar"
            )
    else:
        log.error("Broker provider desconocido: %s (usar 'capital' o 'oanda')", provider)

    return _broker


async def reload_broker(new_environment: str) -> tuple[str, str]:
    """Recrea el broker singleton con un nuevo environment sin restart.

    Pasos:
    1. Pausa scheduler
    2. Cierra broker y orchestrator actuales
    3. Actualiza _current_environment
    4. Recrea broker + orchestrator via _ensure_orchestrator
    5. Valida conexión
    6. Resume scheduler

    Retorna (previous_env, new_env).
    Lanza excepción si falla la conexión con el nuevo env (caller debe rollback).
    """
    global _broker, _orchestrator, _current_environment, _scheduler

    previous = _current_environment or settings.capital_environment
    new_environment = new_environment.upper()

    if previous == new_environment:
        log.info("reload_broker: ya está en %s, no-op", new_environment)
        return previous, new_environment

    log.info("reload_broker: %s → %s", previous, new_environment)

    # 1. Pausar scheduler para evitar jobs concurrentes durante swap
    was_running = _scheduler is not None and _scheduler.running
    if was_running:
        _scheduler.pause()
        # Dar tiempo para que jobs en vuelo terminen
        await asyncio.sleep(1)

    try:
        # 2. Cerrar broker anterior (termina sesión CST en Capital.com)
        if _broker is not None:
            try:
                await _broker.close()
            except Exception:
                log.exception("Error cerrando broker previo — ignorando")
            _broker = None

        # 3. Cerrar orchestrator (tiene ref al broker viejo)
        if _orchestrator is not None:
            try:
                await _orchestrator.close()
            except Exception:
                log.exception("Error cerrando orchestrator previo — ignorando")
            _orchestrator = None

        # 4. Actualizar env cacheado
        _current_environment = new_environment

        # 5. Recrear vía _ensure_orchestrator (lazy)
        orch = _ensure_orchestrator()
        if orch is None:
            raise RuntimeError(f"No se pudo recrear orchestrator para env={new_environment}")

        # 6. Validar conexión autenticando contra Capital.com
        connected = await orch._broker.is_connected()
        if not connected:
            raise RuntimeError(f"Broker no conecta en env={new_environment}")

        log.info("reload_broker: OK en env=%s", new_environment)
    finally:
        if was_running and _scheduler is not None:
            _scheduler.resume()

    return previous, new_environment


def _ensure_orchestrator():
    """Crea el orquestador singleton si aún no existe."""
    global _orchestrator
    broker = _get_broker()
    if broker is None:
        return None

    if _orchestrator is None:
        from app.core.orchestrator import ForexOrchestrator
        _orchestrator = ForexOrchestrator(broker)

    return _orchestrator


async def _run_context_cycle():
    """Fase 1: Analiza H1/H4, corre filtros, cachea instrumentos listos."""
    orch = _ensure_orchestrator()
    if orch is None:
        return
    try:
        await orch.run_context_cycle()
    except Exception:
        log.exception("Error en ciclo de contexto H1/H4")


async def _run_entry_cycle():
    """Fase 2: Busca entradas en M1 para instrumentos listos."""
    orch = _ensure_orchestrator()
    if orch is None:
        return
    try:
        await orch.run_entry_cycle()
    except Exception:
        log.exception("Error en ciclo de entrada M1")


async def _run_position_sync():
    """Sincroniza posiciones con el broker."""
    orch = _ensure_orchestrator()
    if orch is None:
        return

    try:
        from app.db.database import async_session_factory
        async with async_session_factory() as session:
            await orch._manage_positions(session)
            await session.commit()
    except Exception:
        log.exception("Error en sincronización de posiciones")


async def _run_broker_balance_sync():
    """Sincroniza el balance/equity del broker cada 5 min."""
    orch = _ensure_orchestrator()
    if orch is None:
        return
    try:
        await orch.sync_broker_account()
    except Exception:
        log.exception("Error en sync de broker balance")


async def _run_regime_analysis():
    """Analiza el régimen macro cada 60 min (LLM overlay)."""
    orch = _ensure_orchestrator()
    if orch is None:
        return
    try:
        await orch._regime_analyzer.analyze()
    except Exception:
        log.exception("Error en análisis de régimen macro")


async def start_scheduler() -> None:
    global _scheduler

    # Leer environment desde SystemConfig (fallback a .env) ANTES de crear broker
    # Esto asegura que el singleton arranca con el env correcto incluso después de
    # un switch runtime que sobrevivió al restart.
    try:
        env = await get_current_environment()
        log.info("Startup: broker.environment = %s (desde SystemConfig o .env)", env)

        # Seed SystemConfig si no existe: persistir el valor actual para futuros switches
        from app.db.system_config import get_config, set_config
        existing = await get_config("broker.environment")
        if existing is None:
            await set_config("broker.environment", env, updated_by="startup_seed")
            log.info("Seed SystemConfig[broker.environment] = %s", env)
    except Exception:
        log.exception("Error inicializando SystemConfig — seguiremos con .env")

    _scheduler = AsyncIOScheduler()

    # Job 1: Contexto H1/H4 — cada 15 min
    _scheduler.add_job(
        _run_context_cycle,
        trigger=IntervalTrigger(minutes=15),
        id="context_cycle",
        name="Contexto H1/H4 (8 filtros)",
        replace_existing=True,
        max_instances=1,
    )

    # Job 2: Entradas M1 — cada 1 min
    _scheduler.add_job(
        _run_entry_cycle,
        trigger=IntervalTrigger(minutes=1),
        id="entry_cycle",
        name="Entradas M1 (pullback + patrón)",
        replace_existing=True,
        max_instances=1,
    )

    # Job 3: Sync de posiciones — cada 30 segundos
    _scheduler.add_job(
        _run_position_sync,
        trigger=IntervalTrigger(seconds=30),
        id="position_sync",
        name="Sincronización posiciones broker",
        replace_existing=True,
        max_instances=1,
    )

    # Job 4: Sync de balance broker — cada 5 min
    _scheduler.add_job(
        _run_broker_balance_sync,
        trigger=IntervalTrigger(minutes=5),
        id="broker_balance_sync",
        name="Sync balance broker (cada 5 min)",
        replace_existing=True,
        max_instances=1,
    )

    # Job 5: Análisis de régimen macro (LLM overlay) — cada 60 min
    # Corre al arrancar (next_run_time en 90s para dar tiempo al broker auth)
    from datetime import datetime as _dt, timedelta as _td
    _scheduler.add_job(
        _run_regime_analysis,
        trigger=IntervalTrigger(minutes=60),
        id="regime_analysis",
        name="Análisis de régimen macro (LLM, cada 60 min)",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=120,  # Permite ejecutar hasta 2 min tarde
        next_run_time=_dt.now() + _td(seconds=90),  # 90s da tiempo al broker auth
    )

    _scheduler.start()
    log.info(
        "Scheduler Forex iniciado: broker=%s | contexto=15min | entradas=1min | "
        "pos_sync=30seg | balance_sync=5min | regime=60min",
        settings.broker_provider,
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
    """Fuerza un ciclo manual completo (contexto + entradas)."""
    await _run_context_cycle()
    await _run_entry_cycle()
