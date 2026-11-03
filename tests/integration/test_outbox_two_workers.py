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
from datetime import UTC, datetime, timedelta
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
STALE_DELIVERED_EVENT_TYPE = "sec004.stale-delivered"
STALE_FAILED_EVENT_TYPE = "sec004.stale-failed"
STALE_FAILURE_AFTER_DELIVERED_EVENT_TYPE = "sec004.stale-failure-after-delivered"

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
    available_at: datetime | None = None,
    delivering_at: datetime | None = None,
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
            $1, $2, $3::jsonb, $4, $5, $6,
            COALESCE($7::timestamptz, now()),
            CASE WHEN $5::varchar = 'delivered' THEN now() END,
            COALESCE(
                $8::timestamptz,
                CASE WHEN $5::varchar = 'delivering' THEN now() END
            )
        )
        """,
        message_id,
        event_type,
        json.dumps(payload, separators=(",", ":")),
        f"pr2d-{uuid4()}",
        status,
        attempts,
        available_at,
        delivering_at,
    )
    return message_id


async def _fetch_outbox_state(
    database: OutboxDatabase, message_ids: list[UUID]
) -> list[asyncpg.Record]:
    return await database.admin_connection.fetch(
        """
        SELECT id, event_type, status, attempts,
               available_at, delivering_at, delivered_at,
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


async def _pending_claimable_non_test_count(
    database: OutboxDatabase, synthetic_ids: list[UUID]
) -> int:
    count = await database.admin_connection.fetchval(
        """
        SELECT count(*)
          FROM core.outbox
         WHERE status = 'pending'
           AND available_at <= now()
           AND NOT (id = ANY($1::uuid[]))
        """,
        synthetic_ids,
    )
    return int(count or 0)


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
    future_pending_id = await _insert_message(
        outbox_database,
        event_type="existing.application.future",
        payload={"case": "future-pending"},
        available_at=datetime.now(UTC) + timedelta(hours=1),
    )
    fresh_delivering_at = datetime.now(UTC)
    fresh_delivering_id = await _insert_message(
        outbox_database,
        event_type="existing.application.delivering",
        payload={"case": "fresh-delivering"},
        status="delivering",
        attempts=4,
        delivering_at=fresh_delivering_at,
    )
    untouched_ids = [future_pending_id, fresh_delivering_id]
    untouched_before = await _fetch_outbox_state(outbox_database, untouched_ids)
    _require(len(untouched_before) == 2, "Untouched outbox state readback was incomplete")
    untouched_before_by_id = {row["id"]: row for row in untouched_before}
    _require(
        untouched_before_by_id[future_pending_id]["status"] == "pending"
        and untouched_before_by_id[future_pending_id]["available_in_future"]
        and untouched_before_by_id[future_pending_id]["delivering_at"] is None,
        "Future pending control row was not seeded correctly",
    )
    _require(
        untouched_before_by_id[fresh_delivering_id]["status"] == "delivering"
        and untouched_before_by_id[fresh_delivering_id]["attempts"] == 4
        and untouched_before_by_id[fresh_delivering_id]["delivering_at"] is not None,
        "Fresh delivering control row was not seeded correctly",
    )

    pending_non_test_count = await _pending_claimable_non_test_count(outbox_database, message_ids)
    _require(
        pending_non_test_count == 0,
        f"Preflight found pending claimable non-synthetic rows: count={pending_non_test_count}",
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
    except BaseException as error:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        pytest.fail(
            "Concurrent outbox workers did not finish within the timeout; "
            f"exception_type={type(error).__name__}",
            pytrace=False,
        )

    worker_exceptions = [result for result in results if isinstance(result, BaseException)]
    if worker_exceptions:
        exception_types = sorted({type(error).__name__ for error in worker_exceptions})
        pytest.fail(
            "Concurrent outbox worker operation failed; "
            f"exception_types={','.join(exception_types)}",
            pytrace=False,
        )

    states = await _fetch_outbox_state(outbox_database, [*message_ids, *untouched_ids])
    state_by_id = {row["id"]: row for row in states}
    _require(len(state_by_id) == EVENT_COUNT + 2, "Outbox state readback was incomplete")
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

    for message_id in untouched_ids:
        before = untouched_before_by_id[message_id]
        after = state_by_id[message_id]
        _require(
            all(
                before[field] == after[field]
                for field in ("status", "attempts", "available_at", "delivering_at")
            ),
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


async def test_stale_worker_cannot_mark_delivered_after_reclaim(  # noqa: PLR0915 - explicit fence assertions
    outbox_database: OutboxDatabase,
) -> None:
    message_id = await _insert_message(
        outbox_database,
        event_type=STALE_DELIVERED_EVENT_TYPE,
        payload={"case": "sec004-stale-delivered"},
    )
    _require(
        await _pending_claimable_non_test_count(outbox_database, [message_id]) == 0,
        "Preflight found pending claimable non-synthetic rows",
    )

    worker_a_entered = asyncio.Event()
    worker_a_release = asyncio.Event()
    worker_b_entered = asyncio.Event()
    worker_b_release = asyncio.Event()

    async def handler(message: ClaimedMessage) -> None:
        worker = CURRENT_WORKER.get()
        if worker == "worker-a":
            _require(message.attempts == 1, "Stale delivered worker did not claim attempt one")
            worker_a_entered.set()
            await worker_a_release.wait()
        else:
            _require(worker == "worker-b", "Unexpected stale delivered worker identity")
            _require(
                message.attempts == 2, "Replacement delivered worker did not claim attempt two"
            )
            worker_b_entered.set()
            await worker_b_release.wait()

    handlers: dict[str, WorkerHandler] = {STALE_DELIVERED_EVENT_TYPE: handler}

    async def worker(name: str) -> bool:
        token = CURRENT_WORKER.set(name)
        try:
            return await run_once(handlers)
        finally:
            CURRENT_WORKER.reset(token)

    tasks: list[asyncio.Task[bool]] = []
    try:
        async with asyncio.timeout(OPERATION_TIMEOUT):
            worker_a_task = asyncio.create_task(worker("worker-a"))
            tasks.append(worker_a_task)
            await worker_a_entered.wait()

            first_claim = await _fetch_outbox_state(outbox_database, [message_id])
            _require(
                len(first_claim) == 1
                and first_claim[0]["status"] == "delivering"
                and first_claim[0]["attempts"] == 1,
                "First stale delivered claim did not hold attempt one",
            )

            await outbox_database.admin_connection.execute(
                "UPDATE core.outbox SET delivering_at = now() - interval '1 day' WHERE id = $1",
                message_id,
            )
            reclaimed = await reclaim_stuck(age=timedelta(minutes=10))
            _require(reclaimed == 1, "Exactly one stale delivered row was expected to be reclaimed")

            reclaimed_state = await _fetch_outbox_state(outbox_database, [message_id])
            _require(
                len(reclaimed_state) == 1
                and reclaimed_state[0]["status"] == "pending"
                and reclaimed_state[0]["attempts"] == 1,
                "Stale delivered row did not return to pending before replacement claim",
            )

            worker_b_task = asyncio.create_task(worker("worker-b"))
            tasks.append(worker_b_task)
            await worker_b_entered.wait()

            replacement_claim = await _fetch_outbox_state(outbox_database, [message_id])
            _require(
                len(replacement_claim) == 1
                and replacement_claim[0]["status"] == "delivering"
                and replacement_claim[0]["attempts"] == 2,
                "Replacement stale delivered claim did not hold attempt two",
            )

            worker_a_release.set()
            _require(await worker_a_task, "Stale delivered worker did not finish")
            after_stale_delivery = await _fetch_outbox_state(outbox_database, [message_id])
            _require(
                len(after_stale_delivery) == 1
                and after_stale_delivery[0]["status"] == "delivering"
                and after_stale_delivery[0]["attempts"] == 2,
                "Stale worker changed the replacement lease state",
            )

            worker_b_release.set()
            _require(await worker_b_task, "Replacement delivered worker did not finish")
            final = await _fetch_outbox_state(outbox_database, [message_id])
            _require(
                len(final) == 1 and final[0]["status"] == "delivered" and final[0]["attempts"] == 2,
                "Replacement delivered worker did not finish the row",
            )
    except TimeoutError:
        pytest.fail("Stale delivered worker coordination timed out", pytrace=False)
    finally:
        worker_a_release.set()
        worker_b_release.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def test_stale_worker_cannot_mark_failed_after_reclaim(  # noqa: PLR0915 - explicit fence assertions
    outbox_database: OutboxDatabase,
) -> None:
    message_id = await _insert_message(
        outbox_database,
        event_type=STALE_FAILED_EVENT_TYPE,
        payload={"case": "sec004-stale-failed"},
    )
    _require(
        await _pending_claimable_non_test_count(outbox_database, [message_id]) == 0,
        "Preflight found pending claimable non-synthetic rows",
    )

    worker_a_entered = asyncio.Event()
    worker_a_release = asyncio.Event()
    worker_b_entered = asyncio.Event()
    worker_b_release = asyncio.Event()

    async def handler(message: ClaimedMessage) -> None:
        worker = CURRENT_WORKER.get()
        if worker == "worker-a":
            _require(message.attempts == 1, "Stale failed worker did not claim attempt one")
            worker_a_entered.set()
            await worker_a_release.wait()
            raise RuntimeError("synthetic stale failure")
        else:
            _require(worker == "worker-b", "Unexpected stale failed worker identity")
            _require(message.attempts == 2, "Replacement failed worker did not claim attempt two")
            worker_b_entered.set()
            await worker_b_release.wait()

    handlers: dict[str, WorkerHandler] = {STALE_FAILED_EVENT_TYPE: handler}

    async def worker(name: str) -> bool:
        token = CURRENT_WORKER.set(name)
        try:
            return await run_once(handlers)
        finally:
            CURRENT_WORKER.reset(token)

    tasks: list[asyncio.Task[bool]] = []
    try:
        async with asyncio.timeout(OPERATION_TIMEOUT):
            worker_a_task = asyncio.create_task(worker("worker-a"))
            tasks.append(worker_a_task)
            await worker_a_entered.wait()

            first_claim = await _fetch_outbox_state(outbox_database, [message_id])
            _require(
                len(first_claim) == 1
                and first_claim[0]["status"] == "delivering"
                and first_claim[0]["attempts"] == 1,
                "First stale failed claim did not hold attempt one",
            )

            await outbox_database.admin_connection.execute(
                "UPDATE core.outbox SET delivering_at = now() - interval '1 day' WHERE id = $1",
                message_id,
            )
            reclaimed = await reclaim_stuck(age=timedelta(minutes=10))
            _require(reclaimed == 1, "Exactly one stale failed row was expected to be reclaimed")

            reclaimed_state = await _fetch_outbox_state(outbox_database, [message_id])
            _require(
                len(reclaimed_state) == 1
                and reclaimed_state[0]["status"] == "pending"
                and reclaimed_state[0]["attempts"] == 1,
                "Stale failed row did not return to pending before replacement claim",
            )

            worker_b_task = asyncio.create_task(worker("worker-b"))
            tasks.append(worker_b_task)
            await worker_b_entered.wait()
            before_stale_failure = await _fetch_outbox_state(outbox_database, [message_id])
            _require(
                len(before_stale_failure) == 1
                and before_stale_failure[0]["status"] == "delivering"
                and before_stale_failure[0]["attempts"] == 2,
                "Replacement stale failed claim did not hold attempt two",
            )

            worker_a_release.set()
            _require(await worker_a_task, "Stale failed worker did not finish")
            after_stale_failure = await _fetch_outbox_state(outbox_database, [message_id])
            _require(
                len(after_stale_failure) == 1
                and all(
                    after_stale_failure[0][field] == before_stale_failure[0][field]
                    for field in ("status", "attempts", "available_at", "last_error")
                ),
                "Stale worker changed the replacement failure state",
            )

            worker_b_release.set()
            _require(await worker_b_task, "Replacement failed worker did not finish")
            final = await _fetch_outbox_state(outbox_database, [message_id])
            _require(
                len(final) == 1 and final[0]["status"] == "delivered" and final[0]["attempts"] == 2,
                "Replacement failed worker could not continue to delivery",
            )
    except TimeoutError:
        pytest.fail("Stale failed worker coordination timed out", pytrace=False)
    finally:
        worker_a_release.set()
        worker_b_release.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def test_stale_failure_after_replacement_delivered_keeps_row_delivered(  # noqa: PLR0915 - explicit fence assertions
    outbox_database: OutboxDatabase,
) -> None:
    message_id = await _insert_message(
        outbox_database,
        event_type=STALE_FAILURE_AFTER_DELIVERED_EVENT_TYPE,
        payload={"case": "sec004-stale-failure-after-delivered"},
    )
    _require(
        await _pending_claimable_non_test_count(outbox_database, [message_id]) == 0,
        "Preflight found pending claimable non-synthetic rows",
    )

    worker_a_entered = asyncio.Event()
    worker_a_release = asyncio.Event()
    worker_b_entered = asyncio.Event()

    async def handler(message: ClaimedMessage) -> None:
        worker = CURRENT_WORKER.get()
        if worker == "worker-a":
            _require(
                message.attempts == 1,
                "Stale delivered-after-failure worker did not claim attempt one",
            )
            worker_a_entered.set()
            await worker_a_release.wait()
            raise RuntimeError("synthetic stale failure after delivered replacement")
        _require(worker == "worker-b", "Unexpected delivered-after-failure worker identity")
        _require(message.attempts == 2, "Replacement delivered worker did not claim attempt two")
        worker_b_entered.set()

    handlers: dict[str, WorkerHandler] = {STALE_FAILURE_AFTER_DELIVERED_EVENT_TYPE: handler}

    async def worker(name: str) -> bool:
        token = CURRENT_WORKER.set(name)
        try:
            return await run_once(handlers)
        finally:
            CURRENT_WORKER.reset(token)

    tasks: list[asyncio.Task[bool]] = []
    try:
        async with asyncio.timeout(OPERATION_TIMEOUT):
            worker_a_task = asyncio.create_task(worker("worker-a"))
            tasks.append(worker_a_task)
            await worker_a_entered.wait()

            first_claim = await _fetch_outbox_state(outbox_database, [message_id])
            _require(
                len(first_claim) == 1
                and first_claim[0]["status"] == "delivering"
                and first_claim[0]["attempts"] == 1,
                "First delivered-after-failure claim did not hold attempt one",
            )

            await outbox_database.admin_connection.execute(
                "UPDATE core.outbox SET delivering_at = now() - interval '1 day' WHERE id = $1",
                message_id,
            )
            reclaimed = await reclaim_stuck(age=timedelta(minutes=10))
            _require(
                reclaimed == 1,
                "Exactly one stale delivered-after-failure row was expected to be reclaimed",
            )

            reclaimed_state = await _fetch_outbox_state(outbox_database, [message_id])
            _require(
                len(reclaimed_state) == 1
                and reclaimed_state[0]["status"] == "pending"
                and reclaimed_state[0]["attempts"] == 1,
                "Delivered-after-failure row did not return to pending before replacement claim",
            )

            worker_b_task = asyncio.create_task(worker("worker-b"))
            tasks.append(worker_b_task)
            await worker_b_entered.wait()
            _require(await worker_b_task, "Replacement delivered worker did not finish")

            delivered_state = await _fetch_outbox_state(outbox_database, [message_id])
            _require(
                len(delivered_state) == 1
                and delivered_state[0]["status"] == "delivered"
                and delivered_state[0]["attempts"] == 2
                and delivered_state[0]["delivered_at"] is not None
                and delivered_state[0]["last_error"] is None,
                "Replacement worker did not finish a clean delivered state",
            )
            delivered_at = delivered_state[0]["delivered_at"]
            last_error = delivered_state[0]["last_error"]

            worker_a_release.set()
            _require(await worker_a_task, "Stale failure worker did not finish")
            final = await _fetch_outbox_state(outbox_database, [message_id])
            _require(
                len(final) == 1
                and final[0]["status"] == "delivered"
                and final[0]["attempts"] == 2
                and final[0]["delivered_at"] == delivered_at
                and final[0]["last_error"] == last_error,
                "Stale failure changed the delivered replacement row",
            )
    except TimeoutError:
        pytest.fail("Stale failure-after-delivered worker coordination timed out", pytrace=False)
    finally:
        worker_a_release.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


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
