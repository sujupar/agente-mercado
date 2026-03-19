"""Punto de entrada — FastAPI app con lifespan para scheduler y conexiones."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler
from app.db.database import engine, Base, async_session_factory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("agente-mercado")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown del agente."""
    log.info("=== Agente de Mercado iniciando ===")
    log.info("Modo: %s | Capital: $%.2f", settings.agent_mode, settings.initial_capital_usd)

    # Importar modelos y crear tablas si no existen
    from app.db import models  # noqa: F401
    from app.db.models import AgentState, Strategy
    from app.strategies.registry import STRATEGIES

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Tablas verificadas/creadas")

    # Sembrar estrategias si la DB está vacía
    async with async_session_factory() as session:
        from sqlalchemy import select, func
        result = await session.execute(select(func.count(Strategy.id)))
        if result.scalar() == 0:
            log.info("DB vacía — sembrando estrategias...")
            for sid, config in STRATEGIES.items():
                session.add(Strategy(
                    id=config.id, name=config.name,
                    description=config.description, enabled=config.enabled,
                    params={"signal_type": config.signal_type, "direction": config.direction,
                            "instruments": list(config.instruments),
                            "primary_timeframe": config.primary_timeframe,
                            "context_timeframe": config.context_timeframe,
                            "risk_per_trade_pct": config.risk_per_trade_pct,
                            "min_risk_reward": config.min_risk_reward,
                            "max_concurrent_positions": config.max_concurrent_positions,
                            "cycle_interval_minutes": config.cycle_interval_minutes,
                            "trades_per_improvement_cycle": config.trades_per_improvement_cycle},
                    status_text="Activa — esperando señales",
                    llm_budget_fraction=config.llm_budget_fraction,
                ))
                session.add(AgentState(
                    strategy_id=config.id, mode="SIMULATION",
                    capital_usd=config.initial_capital_usd,
                    peak_capital_usd=config.initial_capital_usd,
                ))
                log.info("  Sembrada: %s", config.id)
            await session.commit()

    # Iniciar scheduler
    await start_scheduler()
    log.info("Scheduler iniciado (ciclo cada %d minutos)", settings.cycle_interval_minutes)

    yield

    # Shutdown
    log.info("=== Agente de Mercado deteniendo ===")
    await stop_scheduler()
    await engine.dispose()
    log.info("Recursos liberados. Adiós.")


app = FastAPI(
    title="Agente de Mercado",
    description="Agente autónomo de trading cuantitativo con IA",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — orígenes permitidos (local + producción via env var)
_cors_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5176",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5176",
    "http://localhost:3000",
]
# Agregar origen de producción (Netlify) si está configurado
_frontend_url = os.getenv("FRONTEND_URL", "")
if _frontend_url:
    _cors_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rutas
from app.api.routes import router  # noqa: E402

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"status": "ok", "agent": "Agente de Mercado v0.1.0"}
