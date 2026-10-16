from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core import outbox  # noqa: F401  (register models)
from app.core.config import get_settings
from app.core.db import Base
from app.modules.audit import models as _audit  # noqa: F401
from app.modules.identity import models as _identity  # noqa: F401

target_metadata = Base.metadata


def _run(sync_conn) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=sync_conn, target_metadata=target_metadata, include_schemas=True)
    with context.begin_transaction():
        context.run_migrations()


async def main() -> None:
    settings = get_settings()
    database_url = (
        settings.migration_database_url
        if settings.migration_database_url is not None
        else settings.database_url
    )
    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        await conn.run_sync(_run)
    await engine.dispose()


asyncio.run(main())
