"""Helper para leer/escribir configuración global runtime.

Usa la tabla SystemConfig como key-value store. Permite cambiar
configuración del sistema sin necesidad de editar .env ni reiniciar.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_factory
from app.db.models import SystemConfig

log = logging.getLogger(__name__)


async def get_config(key: str, default: str | None = None) -> str | None:
    """Lee un valor de configuración. Retorna `default` si no existe."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        row = result.scalar_one_or_none()
        return row.value if row else default


async def set_config(key: str, value: str, updated_by: str | None = None) -> None:
    """Escribe o actualiza un valor de configuración (upsert)."""
    async with async_session_factory() as session:
        stmt = insert(SystemConfig).values(
            key=key, value=value, updated_by=updated_by,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["key"],
            set_={"value": value, "updated_by": updated_by},
        )
        await session.execute(stmt)
        await session.commit()
    log.info("SystemConfig[%s] = %s (by %s)", key, value, updated_by or "system")


async def get_config_with_session(
    session: AsyncSession, key: str, default: str | None = None,
) -> str | None:
    """Variante con session externa (para usar dentro de una transacción)."""
    result = await session.execute(
        select(SystemConfig).where(SystemConfig.key == key)
    )
    row = result.scalar_one_or_none()
    return row.value if row else default
