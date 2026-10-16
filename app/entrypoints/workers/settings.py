"""arq worker. Jobs carry references only, never secrets (S-019)."""

from __future__ import annotations

from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.request_context import set_request_id
from app.entrypoints.workers.arq_jobs import outbox_tick
from app.entrypoints.workers.arq_jobs import shutdown as outbox_shutdown
from app.entrypoints.workers.arq_jobs import startup as outbox_startup


async def deliver_outbox(ctx: dict[str, Any], request_id: str) -> None:
    set_request_id(request_id)
    # Phase 3+: poll core.outbox with SKIP LOCKED, dispatch to adapters, mark delivered.


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging(get_settings().log_level)
    await outbox_startup(ctx)


class WorkerSettings:
    functions: ClassVar[list[Any]] = [deliver_outbox, outbox_tick]
    on_startup = startup
    on_shutdown = outbox_shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_tries = 5
    job_timeout = 120
