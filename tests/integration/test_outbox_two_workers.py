"""Two-worker outbox claim, reclaim, and retry timing checks."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import Counter
from collections.abc import AsyncIterator, Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest
from sqlalchemy.engine import make_url

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import app.core.db as app_database  # noqa: E402
from app.core.db import unit_of_work  # noqa: E402
from app.core.outbox_dispatch import (  # noqa: E402
    ClaimedMessage,
    backoff,
    mark_failed,
)
from app.entrypoints.workers.outbox_runner import reclaim_stuck, run_once  # noqa: E402

CONNECT_TIMEOUT = 5
QUERY_TIMEOUT = 5
OPERATION_TIMEOUT = 30
CLEANUP_TIMEOUT = 3
EVENT_COUNT = 10
SYNTHETIC_EVENT_TYPE = "pr2d.synthetic"
RECLAIM_EVENT_TYPE = "pr2d.reclaim"
FAILED_EVENT_TYPE = "pr2d.failed"

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="requires disposable PostgreSQL and RUN_INTEGRATION=1",
)

WorkerHandler = Callable[[ClaimedMessage], Awaitable[None]]
CURRENT_WORKER: ContextVar[str] = ContextVar("pr2d_current_worker", default="unknown")


@dataclass(repr=False)
class OutboxDatabase:
    runtime_connection: asyncpg.Connection = field(repr=False)
    admin_connection: asyncpg.Connection = field(repr=False)
    registered_ids: set[UUID] = field(default_factory=set)

    def register(self, message_id: UUID) -> None:
        self.registered_ids.add(message_id)


def _require(condition: bool, message: str) -> None:
    # Keep UUIDs, payloads, and database objects out of pytest's assertion introspection.
    if not condition:
        pytest.fail(message, pytrace=False)


def _database_dsn(environment_name: str, expected_user: str) -> str | None:
    raw_url = os.getenv(environment_name, "").strip()
    if not raw_url:
        return None
    try:
        parsed = make_url(raw_url)
        if parsed.drivername not in {"postgres", "postgresql", "postgresql+asyncpg"}:
            return None
        if parsed.username != expected_user:
            return None
        return parsed.set(drivername="postgresql").render_as_string(hide_password=False)
    except Exception:
        return None


async def _close_connection(connection: asyncpg.Connection | None) -> bool:
    if connection is None:
        return True
    try:
        async with asyncio.timeout(CLEANUP_TIMEOUT):
            await connection.close(timeout=CLEANUP_TIMEOUT)
    except BaseException:
        return False
    return True


async def _reset_application_database() -> bool:
    engine = app_database._engine
    app_database._sessionmaker = None
    app_database._engine = None
    if engine is None:
        return True
    try:
        async with asyncio.timeout(CLEANUP_TIMEOUT):
            await engine.dispose()
    except BaseException:
        return False
    return True


async def _connect(dsn: str) -> asyncpg.Connection | None:
    try:
        async with asyncio.timeout(CONNECT_TIMEOUT):
            return await asyncpg.connect(
                dsn=dsn,
                timeout=CONNECT_TIMEOUT,
                command_timeout=QUERY_TIMEOUT,
                server_settings={
                    "statement_timeout": str(QUERY_TIMEOUT * 1000),
                    "lock_timeout": str(QUERY_TIMEOUT * 1000),
                    "idle_in_transaction_session_timeout": str(
                        (QUERY_TIMEOUT + CLEANUP_TIMEOUT) * 1000
                    ),
                },
            )
    except BaseException:
        return None


async def _cleanup(database: OutboxDatabase) -> bool:
    if not database.registered_ids:
        return True
    try:
        async with asyncio.timeout(OPERATION_TIMEOUT):
            identity = await database.admin_connection.fetchrow("SELECT current_user, session_user")
            if identity is None or identity["current_user"] != identity["session_user"]:
                return False
            if identity["current_user"] != "sentinel_admin":
                return False
            ids = list(database.registered_ids)
            await database.admin_connection.execute(
                "DELETE FROM core.outbox WHERE id = ANY($1::uuid[])", ids
            )
            remaining = await database.admin_connection.fetchval(
                "SELECT count(*) FROM core.outbox WHERE id = ANY($1::uuid[])", ids
            )
            return remaining == 0
    except BaseException:
        return False


@pytest.fixture
async def outbox_database() -> AsyncIterator[OutboxDatabase]:
    if not await _reset_application_database():
        pytest.fail("Application database engine reset failed", pytrace=False)

    required = ("DATABASE_URL", "MIGRATION_DATABASE_URL")
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        pytest.fail("Missing outbox integration environment: " + ", ".join(missing), pytrace=False)

    runtime_dsn = _database_dsn("DATABASE_URL", "sentinel_app")
    admin_dsn = _database_dsn("MIGRATION_DATABASE_URL", "sentinel_admin")
    if runtime_dsn is None or admin_dsn is None or runtime_dsn == admin_dsn:
        pytest.fail(
            "Outbox PostgreSQL roles or drivers are not configured separately", pytrace=False
        )

    runtime_connection = await _connect(runtime_dsn)
    admin_connection = await _connect(admin_dsn)
    setup_failed = runtime_connection is None or admin_connection is None
    if not setup_failed:
        try:
            runtime_identity = await runtime_connection.fetchrow(
                "SELECT current_user, session_user, current_database() AS database_name"
            )
            admin_identity = await admin_connection.fetchrow(
                "SELECT current_user, session_user, current_database() AS database_name"
            )
            setup_failed = (
                runtime_identity is None
                or admin_identity is None
                or runtime_identity["current_user"] != "sentinel_app"
                or runtime_identity["session_user"] != "sentinel_app"
                or admin_identity["current_user"] != "sentinel_admin"
                or admin_identity["session_user"] != "sentinel_admin"
                or runtime_identity["database_name"] != admin_identity["database_name"]
            )
        except BaseException:
            setup_failed = True

    if setup_failed or runtime_connection is None or admin_connection is None:
        await _close_connection(runtime_connection)
        await _close_connection(admin_connection)
        pytest.fail(
            "Outbox PostgreSQL runtime/admin connection or role check failed", pytrace=False
        )

    database = OutboxDatabase(runtime_connection, admin_connection)
    try:
        yield database
    finally:
        cleaned = await _cleanup(database)
        runtime_closed = await _close_connection(runtime_connection)
        admin_closed = await _close_connection(admin_connection)
        application_closed = await _reset_application_database()
        _require(
            cleaned and runtime_closed and admin_closed and application_closed,
            "Outbox scoped admin cleanup or connection close failed",
        )


async def _insert_message(
    database: OutboxDatabase,
    *,
    event_type: str,
    payload: dict[str, object],
    status: str = "pending",
    attempts: int = 0,
) -> UUID:
    message_id = uuid4()
    database.register(message_id)
    await database.runtime_connection.execute(
        """
        INSERT INTO core.outbox (
            id, event_type, payload, request_id, status, attempts,
            available_at, delivered_at, delivering_at
        )
        VALUES (
            $1, $2, $3::jsonb, $4, $5, $6, now(),
            CASE WHEN $5::varchar = 'delivered' THEN now() END,
            CASE WHEN $5::varchar = 'delivering' THEN now() END
        )
        """,
        message_id,
        event_type,
        json.dumps(payload, separators=(",", ":")),
        f"pr2d-{uuid4()}",
        status,
        attempts,
    )
    return message_id


async def _fetch_outbox_state(
    database: OutboxDatabase, message_ids: list[UUID]
) -> list[asyncpg.Record]:
    return await database.admin_connection.fetch(
        """
        SELECT id, event_type, status, attempts,
               available_at <= now() AS available,
               available_at > now() AS available_in_future,
               delivering_at IS NULL AS delivery_timestamp_clear,
               delivered_at IS NOT NULL AS delivered_timestamp_set,
               last_error
          FROM core.outbox
         WHERE id = ANY($1::uuid[])
         ORDER BY id
        """,
        message_ids,
    )


async def test_two_workers_claim_each_synthetic_event_once(  # noqa: PLR0915 - explicit gate assertions
    outbox_database: OutboxDatabase,
) -> None:
    message_ids = [
        await _insert_message(
            outbox_database,
            event_type=SYNTHETIC_EVENT_TYPE,
            payload={"case": "two-workers", "ordinal": ordinal},
        )
        for ordinal in range(EVENT_COUNT)
    ]
    untouched_id = await _insert_message(
        outbox_database,
        event_type="existing.application.event",
        payload={"case": "non-target"},
        status="delivered",
        attempts=7,
    )

    counts: Counter[UUID] = Counter()
    worker_hits: Counter[str] = Counter()
    handler_entries = 0
    handler_lock = asyncio.Lock()
    worker_barrier = asyncio.Barrier(2)
    handler_barrier = asyncio.Barrier(2)

    async def handler(message: ClaimedMessage) -> None:
        nonlocal handler_entries
        async with handler_lock:
            counts[message.id] += 1
            worker_hits[CURRENT_WORKER.get()] += 1
            handler_entries += 1
            entry_number = handler_entries
        if entry_number <= 2:
            await handler_barrier.wait()

    handlers: dict[str, WorkerHandler] = {SYNTHETIC_EVENT_TYPE: handler}

    async def worker(name: str) -> None:
        token = CURRENT_WORKER.set(name)
        try:
            await worker_barrier.wait()
            while True:
                if not await run_once(handlers):
                    break
        finally:
            CURRENT_WORKER.reset(token)

    tasks = [asyncio.create_task(worker("worker-a")), asyncio.create_task(worker("worker-b"))]
    try:
        async with asyncio.timeout(OPERATION_TIMEOUT):
            results = await asyncio.gather(*tasks, return_exceptions=True)
    except BaseException:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        pytest.fail("Concurrent outbox workers did not finish within the timeout", pytrace=False)

    if any(isinstance(result, BaseException) for result in results):
        pytest.fail("Concurrent outbox worker operation failed", pytrace=False)

    states = await _fetch_outbox_state(outbox_database, [*message_ids, untouched_id])
    state_by_id = {row["id"]: row for row in states}
    _require(len(state_by_id) == EVENT_COUNT + 1, "Outbox state readback was incomplete")
    _require(set(counts) == set(message_ids), "Synthetic handler coverage was incomplete")
    _require(
        all(counts[message_id] == 1 for message_id in message_ids),
        "Handler duplicate detected",
    )
    _require(sum(counts.values()) == EVENT_COUNT, "Synthetic handler call count was incorrect")
    _require(
        worker_hits["worker-a"] > 0 and worker_hits["worker-b"] > 0,
        "Both workers did not claim work",
    )

    for message_id in message_ids:
        row = state_by_id[message_id]
        _require(
            row["event_type"] == SYNTHETIC_EVENT_TYPE
            and row["status"] == "delivered"
            and row["attempts"] == 1
            and row["delivery_timestamp_clear"]
            and row["delivered_timestamp_set"],
            "Synthetic outbox row did not reach delivered with one attempt",
        )

    untouched = state_by_id[untouched_id]
    _require(
        untouched["event_type"] == "existing.application.event"
        and untouched["status"] == "delivered"
        and untouched["attempts"] == 7
        and untouched["delivery_timestamp_clear"]
        and untouched["delivered_timestamp_set"],
        "Non-target outbox row was claimed or changed",
    )
    print(f"outbox two-workers: events={EVENT_COUNT} handler_calls={sum(counts.values())}")


async def test_reclaim_stuck_delivery_then_delivers_once(
    outbox_database: OutboxDatabase,
) -> None:
    message_id = await _insert_message(
        outbox_database,
        event_type=RECLAIM_EVENT_TYPE,
        payload={"case": "reclaim"},
        status="delivering",
        attempts=1,
    )
    await outbox_database.admin_connection.execute(
        "UPDATE core.outbox SET delivering_at = now() - interval '1 day' WHERE id = $1",
        message_id,
    )

    before = await _fetch_outbox_state(outbox_database, [message_id])
    _require(
        len(before) == 1 and before[0]["status"] == "delivering",
        "Stale synthetic delivery was not seeded as delivering",
    )

    reclaimed = await reclaim_stuck(age=timedelta(minutes=10))
    _require(reclaimed == 1, "Exactly one stale outbox row was expected to be reclaimed")
    pending = await _fetch_outbox_state(outbox_database, [message_id])
    _require(
        len(pending) == 1
        and pending[0]["status"] == "pending"
        and pending[0]["attempts"] == 1
        and pending[0]["available"]
        and pending[0]["delivery_timestamp_clear"],
        "Reclaimed outbox row did not return to pending",
    )

    calls: Counter[UUID] = Counter()

    async def handler(message: ClaimedMessage) -> None:
        calls[message.id] += 1

    delivered = await run_once({RECLAIM_EVENT_TYPE: handler})
    no_duplicate = await run_once({RECLAIM_EVENT_TYPE: handler})
    final = await _fetch_outbox_state(outbox_database, [message_id])
    _require(delivered and not no_duplicate, "Reclaimed outbox row was not delivered exactly once")
    _require(calls[message_id] == 1, "Reclaimed outbox handler was invoked more than once")
    _require(
        len(final) == 1
        and final[0]["status"] == "delivered"
        and final[0]["attempts"] == 2
        and final[0]["delivery_timestamp_clear"]
        and final[0]["delivered_timestamp_set"],
        "Reclaimed outbox row did not finish delivered with the expected attempt count",
    )
    print("outbox reclaim: reclaimed=1 handler_calls=1")


async def test_mark_failed_backoff_sets_a_future_retry_time(
    outbox_database: OutboxDatabase,
) -> None:
    message_id = await _insert_message(
        outbox_database,
        event_type=FAILED_EVENT_TYPE,
        payload={"case": "mark-failed"},
        status="delivering",
        attempts=2,
    )

    async with unit_of_work() as session:
        await mark_failed(session, message_id, attempts=2, error="synthetic failure")

    state = await _fetch_outbox_state(outbox_database, [message_id])
    _require(len(state) == 1, "Failed outbox state readback was incomplete")
    _require(
        state[0]["status"] == "pending"
        and state[0]["attempts"] == 2
        and state[0]["available_in_future"]
        and state[0]["delivery_timestamp_clear"]
        and state[0]["last_error"] == "synthetic failure",
        "mark_failed did not schedule the expected retry state",
    )
    _require(backoff(2) == timedelta(seconds=2), "Backoff calculation changed unexpectedly")
    print("outbox mark-failed: retry_scheduled=true")
