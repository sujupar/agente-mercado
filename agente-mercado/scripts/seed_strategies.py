"""Script para recrear tablas y sembrar datos iniciales de las estrategias Forex."""

import asyncio
import sys
from pathlib import Path

# Asegurar que el path del proyecto esta en sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.database import engine, Base
from app.db import models  # noqa: F401 — importa todos los modelos para que Base los conozca
from app.db.database import async_session_factory
from app.db.models import AgentState, Strategy
from app.strategies.registry import STRATEGIES


async def main():
    print("=== Semilla de Estrategias Forex (Oliver Vélez) ===\n")

    # 1. Recrear TODAS las tablas (drop + create)
    print("1. Recreando tablas...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("   Tablas recreadas exitosamente.\n")

    # 2. Insertar estrategias + AgentStates
    print("2. Insertando estrategias y estados iniciales...")
    async with async_session_factory() as session:
        for sid, config in STRATEGIES.items():
            # Strategy
            strategy = Strategy(
                id=config.id,
                name=config.name,
                description=config.description,
                enabled=config.enabled,
                params={
                    "signal_type": config.signal_type,
                    "direction": config.direction,
                    "instruments": list(config.instruments),
                    "primary_timeframe": config.primary_timeframe,
                    "context_timeframe": config.context_timeframe,
                    "risk_per_trade_pct": config.risk_per_trade_pct,
                    "min_risk_reward": config.min_risk_reward,
                    "max_concurrent_positions": config.max_concurrent_positions,
                    "cycle_interval_minutes": config.cycle_interval_minutes,
                    "trades_per_improvement_cycle": config.trades_per_improvement_cycle,
                },
                status_text="Activa — esperando señales",
                llm_budget_fraction=config.llm_budget_fraction,
            )
            session.add(strategy)

            # AgentState
            state = AgentState(
                strategy_id=config.id,
                mode="SIMULATION",
                capital_usd=config.initial_capital_usd,
                peak_capital_usd=config.initial_capital_usd,
            )
            session.add(state)

            print(f"   [{config.id}] {config.name} — ${config.initial_capital_usd:,.0f} — {config.direction}")

        await session.commit()

    print("\n3. Verificando...")
    async with async_session_factory() as session:
        from sqlalchemy import select, func

        result = await session.execute(select(func.count(Strategy.id)))
        strat_count = result.scalar()
        print(f"   Estrategias: {strat_count}")

        result = await session.execute(select(func.count(AgentState.id)))
        state_count = result.scalar()
        print(f"   Agent States: {state_count}")

        result = await session.execute(
            select(Strategy.id, Strategy.name, Strategy.enabled)
        )
        for row in result.all():
            status = "activa" if row[2] else "deshabilitada"
            print(f"   - {row[0]}: {row[1]} ({status})")

    print("\n=== Semilla completada exitosamente ===")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
