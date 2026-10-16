from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from app.entrypoints.workers.outbox_runner import Handler, reclaim_stuck, run_once

# Keep empty until concrete handlers exist. Never claim work into a scaffold.
HANDLERS: dict[str, Handler] = {}


async def outbox_tick(ctx: dict[str, Any]) -> None:
    await reclaim_stuck(age=timedelta(minutes=10))
    if HANDLERS:
        await run_once(HANDLERS)


async def outbox_loop(ctx: dict[str, Any]) -> None:
    while not ctx.get("stopping", False):
        await outbox_tick(ctx)
        await asyncio.sleep(1)


async def startup(ctx: dict[str, Any]) -> None:
    ctx["outbox_task"] = asyncio.create_task(outbox_loop(ctx))


async def shutdown(ctx: dict[str, Any]) -> None:
    ctx["stopping"] = True
    task = ctx.get("outbox_task")
    if task:
        task.cancel()
        try:  # noqa: SIM105 - explicit cancellation handling is intentional
            await task
        except asyncio.CancelledError:
            pass
