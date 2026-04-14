"""Scheduler Forex — APScheduler dual (DEMO + LIVE en paralelo).

Mantiene un dict de brokers y orchestrators indexado por environment.
Jobs duplicados con sufijo env para correr ambos ambientes simultáneamente.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

log = logging.getLogger(__name__)

# Estados globales indexados por environment
_scheduler: AsyncIOScheduler | None = None
_brokers: dict[str, object] = {}  # {"DEMO": BrokerInterface, "LIVE": ...}
_orchestrators: dict[str, object] = {}  # {"DEMO": ForexOrchestrator, "LIVE": ...}


ENVIRONMENTS = ("DEMO", "LIVE")


def _credentials_for(env: str) -> tuple[str, str, str] | None:
    """Retorna (api_key, identifier, password) para el environment, o None si faltan."""
    env = env.upper()
    if env == "DEMO":
        if settings.capital_api_key and settings.capital_identifier:
            return (
                settings.capital_api_key,
                settings.capital_identifier,
                settings.capital_password,
            )
        return None
    if env == "LIVE":
        if settings.capital_api_key_live and settings.capital_identifier_live:
            return (
                settings.capital_api_key_live,
                settings.capital_identifier_live,
                settings.capital_password_live,
            )
        return None
    return None


def _get_broker(env: str):
    """Crea (o retorna cached) el broker para el environment dado."""
    env = env.upper()
    if env in _brokers:
        return _brokers[env]

    provider = settings.broker_provider.lower()

    if provider == "capital":
        creds = _credentials_for(env)
        if creds is None:
            log.info(
                "Broker %s no configurado (faltan credenciales CAPITAL_*%s) — "
                "este environment no operará",
                env,
                "" if env == "DEMO" else "_LIVE",
            )
            return None

        from app.broker.capital import CapitalBroker
        api_key, identifier, password = creds
        broker = CapitalBroker(
            api_key=api_key,
            identifier=identifier,
            password=password,
            environment=env,
        )
        _brokers[env] = broker
        log.info("Broker Capital.com inicializado: env=%s", env)
        return broker

    if provider == "oanda":
        # OANDA legacy — solo soporta un entorno por ahora
        if env != "DEMO":
            log.info("OANDA no soporta dual env — solo DEMO")
            return None
        from app.broker.oanda import OANDABroker
        if settings.oanda_account_id and settings.oanda_access_token:
            broker = OANDABroker(
                account_id=settings.oanda_account_id,
                access_token=settings.oanda_access_token,
                environment=settings.oanda_environment,
            )
            _brokers[env] = broker
            log.info("Broker OANDA inicializado: env=%s", settings.oanda_environment)
            return broker
        return None

    log.error("Broker provider desconocido: %s", provider)
    return None


def _ensure_orchestrator(env: str):
    """Crea (o retorna cached) el orchestrator para el environment dado."""
    env = env.upper()
    broker = _get_broker(env)
    if broker is None:
        return None

    if env in _orchestrators:
        return _orchestrators[env]

    from app.core.orchestrator import ForexOrchestrator
    orch = ForexOrchestrator(broker, environment=env)
    _orchestrators[env] = orch
    log.info("Orchestrator inicializado: env=%s", env)
    return orch


# ── Job runners por environment ────────────────────────────────

def _make_runner(coro_name: str, env: str):
    """Factory de funciones async que ejecutan un método del orchestrator por env."""
    env = env.upper()

    async def runner():
        orch = _ensure_orchestrator(env)
        if orch is None:
            return
        try:
            if coro_name == "run_context_cycle":
                await orch.run_context_cycle()
            elif coro_name == "run_entry_cycle":
                await orch.run_entry_cycle()
            elif coro_name == "run_position_sync":
                from app.db.database import async_session_factory
                async with async_session_factory() as session:
                    await orch._manage_positions(session)
                    await session.commit()
            elif coro_name == "run_broker_balance_sync":
                await orch.sync_broker_account()
            elif coro_name == "run_regime_analysis":
                await orch._regime_analyzer.analyze()
        except Exception:
            log.exception("Error en job %s (env=%s)", coro_name, env)

    runner.__name__ = f"_run_{coro_name}_{env}"
    return runner


# ── Compatibilidad: get_current_environment legacy ────────────

async def get_current_environment() -> str:
    """[LEGACY] Retorna 'DEMO' (compat con código anterior que asumía singleton).

    En dual-mode, el concepto de "environment activo" ya no aplica — ambos corren
    en paralelo. Se mantiene esta función para callers legacy, devolviendo DEMO
    como default (el env 'principal').
    """
    return "DEMO"


async def reload_broker(new_environment: str) -> tuple[str, str]:
    """[DEPRECATED] El switch DEMO↔LIVE exclusivo ya no aplica.

    En dual-mode, ambos ambientes corren simultáneamente si sus credenciales
    están configuradas. Esta función se mantiene por compat pero es no-op.
    """
    log.warning(
        "reload_broker() es deprecated en dual-mode — ambos ambientes corren en paralelo"
    )
    return (new_environment.upper(), new_environment.upper())


# ── Startup / shutdown ────────────────────────────────────────

async def start_scheduler() -> None:
    """Arranca el scheduler con jobs duplicados por environment."""
    global _scheduler

    # Seed SystemConfig (compatibilidad): si no existe, setea DEMO
    try:
        from app.db.system_config import get_config, set_config
        existing = await get_config("broker.environment")
        if existing is None:
            await set_config("broker.environment", "DEMO", updated_by="startup_seed")
            log.info("Seed SystemConfig[broker.environment] = DEMO (dual-mode activo)")
    except Exception:
        log.exception("Error inicializando SystemConfig — seguiremos sin seed")

    _scheduler = AsyncIOScheduler()

    # Detectar qué ambientes tienen credenciales configuradas
    active_envs = []
    for env in ENVIRONMENTS:
        if _credentials_for(env) is not None:
            active_envs.append(env)

    if not active_envs:
        log.error(
            "No hay credenciales configuradas para ningún environment. "
            "El scheduler no registrará jobs."
        )
        _scheduler.start()
        return

    log.info("Dual-mode activo: ambientes disponibles = %s", active_envs)

    # Registrar jobs por environment
    from datetime import datetime as _dt, timedelta as _td
    for env in active_envs:
        # Job: Contexto H1/H4 — cada 15 min
        _scheduler.add_job(
            _make_runner("run_context_cycle", env),
            trigger=IntervalTrigger(minutes=15),
            id=f"context_cycle_{env}",
            name=f"Contexto H1/H4 ({env})",
            replace_existing=True,
            max_instances=1,
        )
        # Job: Entradas M1 — cada 1 min
        _scheduler.add_job(
            _make_runner("run_entry_cycle", env),
            trigger=IntervalTrigger(minutes=1),
            id=f"entry_cycle_{env}",
            name=f"Entradas M1 ({env})",
            replace_existing=True,
            max_instances=1,
        )
        # Job: Sync posiciones — cada 30s
        _scheduler.add_job(
            _make_runner("run_position_sync", env),
            trigger=IntervalTrigger(seconds=30),
            id=f"position_sync_{env}",
            name=f"Sync posiciones ({env})",
            replace_existing=True,
            max_instances=1,
        )
        # Job: Sync balance — cada 5 min
        _scheduler.add_job(
            _make_runner("run_broker_balance_sync", env),
            trigger=IntervalTrigger(minutes=5),
            id=f"broker_balance_sync_{env}",
            name=f"Sync balance broker ({env})",
            replace_existing=True,
            max_instances=1,
        )

    # Job: Regime analysis — solo UNA vez (es macro, aplica a ambos ambientes)
    # Lo registramos en el primer env disponible
    _scheduler.add_job(
        _make_runner("run_regime_analysis", active_envs[0]),
        trigger=IntervalTrigger(minutes=60),
        id="regime_analysis",
        name=f"Régimen macro ({active_envs[0]} — overlay compartido)",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=120,
        next_run_time=_dt.now() + _td(seconds=90),
    )

    _scheduler.start()
    log.info(
        "Scheduler Forex iniciado (dual-mode): envs=%s | broker=%s",
        active_envs,
        settings.broker_provider,
    )


async def stop_scheduler() -> None:
    """Detiene scheduler y cierra todos los brokers/orchestrators."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("Scheduler detenido")

    for env, orch in list(_orchestrators.items()):
        try:
            await orch.close()
        except Exception:
            log.exception("Error cerrando orchestrator %s", env)
    _orchestrators.clear()

    for env, broker in list(_brokers.items()):
        try:
            await broker.close()
        except Exception:
            log.exception("Error cerrando broker %s", env)
    _brokers.clear()


async def trigger_manual_cycle(environment: str = "DEMO") -> None:
    """Fuerza un ciclo manual completo (contexto + entradas) para un env."""
    env = environment.upper()
    orch = _ensure_orchestrator(env)
    if orch is None:
        log.warning("trigger_manual_cycle: env=%s no disponible", env)
        return
    try:
        await orch.run_context_cycle()
        await orch.run_entry_cycle()
    except Exception:
        log.exception("Error en trigger_manual_cycle env=%s", env)


# ── API pública para otros módulos ────────────────────────────

def get_broker(env: str = "DEMO"):
    """Accesor público para obtener el broker de un env (usado por routes.py)."""
    return _get_broker(env)


def get_active_environments() -> list[str]:
    """Lista de environments con credenciales configuradas."""
    return [env for env in ENVIRONMENTS if _credentials_for(env) is not None]


def is_env_connected(env: str) -> bool:
    """Retorna True si el broker del env existe en el dict (fue creado)."""
    return env.upper() in _brokers
