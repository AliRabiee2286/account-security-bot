"""Concurrent one-time-form consumption checks for disposable PostgreSQL."""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import bindparam, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.one_time_form_store import ConsumedForm, consume_form, issue_form  # noqa: E402
from app.core.token_hash import hash_token  # noqa: E402

RACE_REPETITIONS = 20
FORM_PURPOSE = "credential_entry"
FORM_OWNER_TYPE = "social_account"
CONNECT_TIMEOUT = 5
QUERY_TIMEOUT = 5
OPERATION_TIMEOUT = 15
CLOSE_TIMEOUT = 5
PAIR_TIMEOUT = 20

IDENTITY_QUERY = text("SELECT current_user, session_user, pg_backend_pid()")

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="requires disposable PostgreSQL and RUN_INTEGRATION=1",
)


@dataclass(repr=False)
class RaceDatabase:
    runtime_sessions: async_sessionmaker[AsyncSession]
    runtime_engine: AsyncEngine
    admin_engine: AsyncEngine
    synthetic_hashes: set[str] = field(default_factory=set)

    def register(self, raw_token: str) -> None:
        self.synthetic_hashes.add(hash_token(raw_token))


@dataclass(frozen=True)
class SyntheticForm:
    raw_token: str = field(repr=False)
    subject_id: UUID
    owner_id: UUID


def _require(condition: bool, message: str) -> None:
    # Do not let pytest introspect expressions containing tokens or database objects.
    if not condition:
        pytest.fail(message, pytrace=False)


def _database_url(raw_url: str, expected_user: str) -> str | None:
    try:
        parsed = make_url(raw_url)
        if parsed.drivername != "postgresql+asyncpg" or parsed.username != expected_user:
            return None
    except Exception:
        return None
    return raw_url


async def _release(close: Callable[[], Awaitable[None]]) -> bool:
    """Bound resource teardown and keep driver errors out of pytest reports."""
    try:
        async with asyncio.timeout(CLOSE_TIMEOUT):
            await close()
    except BaseException:
        return False
    return True


async def _probe(engine: AsyncEngine, expected_user: str) -> bool:
    connection: AsyncConnection | None = None
    failed = False
    correct_role = False
    try:
        async with asyncio.timeout(OPERATION_TIMEOUT):
            connection = engine.connect()
            await connection.start()
            identity = (await connection.execute(IDENTITY_QUERY)).one()
            correct_role = identity[0] == identity[1] == expected_user
    except BaseException:
        failed = True
    closed = connection is None or await _release(connection.close)
    return not failed and correct_role and closed


async def _dispose(engine: AsyncEngine | None) -> bool:
    return engine is None or await _release(engine.dispose)


async def _runtime_operation[T](
    database: RaceDatabase, operation: Callable[[AsyncSession], Awaitable[T]]
) -> T:
    session: AsyncSession | None = None
    value: T | None = None
    failed = False
    try:
        async with asyncio.timeout(OPERATION_TIMEOUT):
            session = database.runtime_sessions()
            value = await operation(session)
    except BaseException:
        failed = True
    closed = session is None or await _release(session.close)
    # A callback lets the original exception fully unwind before reporting failure.
    # Raising from an async context manager's __aexit__ would retain its context.
    _require(closed, "Runtime PostgreSQL session close failed or timed out")
    _require(not failed, "Runtime PostgreSQL operation failed or timed out")
    return cast(T, value)


async def _cleanup(database: RaceDatabase) -> bool:
    if not database.synthetic_hashes:
        return True
    parameters = {"token_hashes": tuple(database.synthetic_hashes)}
    delete = text("DELETE FROM social.one_time_forms WHERE token_hash IN :token_hashes")
    count = text("SELECT count(*) FROM social.one_time_forms WHERE token_hash IN :token_hashes")
    delete = delete.bindparams(bindparam("token_hashes", expanding=True))
    count = count.bindparams(bindparam("token_hashes", expanding=True))
    connection: AsyncConnection | None = None
    failed = False
    empty = False
    try:
        async with asyncio.timeout(OPERATION_TIMEOUT):
            connection = database.admin_engine.connect()
            await connection.start()
            identity = (await connection.execute(IDENTITY_QUERY)).one()
            if identity[0] != "sentinel_admin" or identity[1] != "sentinel_admin":
                raise RuntimeError("cleanup requires the actual sentinel_admin role")
            await connection.execute(delete, parameters)
            await connection.commit()
            # This read starts a new transaction after the scoped DELETE has committed.
            empty = (await connection.execute(count, parameters)).scalar_one() == 0
    except BaseException:
        failed = True
    closed = connection is None or await _release(connection.close)
    return not failed and empty and closed


@pytest.fixture
async def race_database() -> AsyncIterator[RaceDatabase]:
    required = ("DATABASE_URL", "MIGRATION_DATABASE_URL")
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        pytest.fail("Missing race integration environment: " + ", ".join(missing), pytrace=False)

    runtime_url = _database_url(os.environ["DATABASE_URL"], "sentinel_app")
    admin_url = _database_url(os.environ["MIGRATION_DATABASE_URL"], "sentinel_admin")
    if runtime_url is None or admin_url is None or runtime_url == admin_url:
        pytest.fail("Race PostgreSQL roles or driver are not configured separately", pytrace=False)

    runtime_engine: AsyncEngine | None = None
    admin_engine: AsyncEngine | None = None
    setup_failed = False
    try:
        engine_options = {
            "pool_pre_ping": True,
            "pool_size": 2,
            "max_overflow": 0,
            "pool_timeout": CONNECT_TIMEOUT,
            "hide_parameters": True,
            "echo": False,
            "echo_pool": False,
            "connect_args": {
                "timeout": CONNECT_TIMEOUT,
                "command_timeout": QUERY_TIMEOUT,
                "server_settings": {
                    "statement_timeout": str(QUERY_TIMEOUT * 1000),
                    "lock_timeout": str(QUERY_TIMEOUT * 1000),
                    "idle_in_transaction_session_timeout": str(OPERATION_TIMEOUT * 1000),
                },
            },
        }
        runtime_engine = create_async_engine(runtime_url, **engine_options)
        admin_engine = create_async_engine(admin_url, **engine_options)
        if not await _probe(runtime_engine, "sentinel_app") or not await _probe(
            admin_engine, "sentinel_admin"
        ):
            setup_failed = True
    except BaseException:
        setup_failed = True

    if setup_failed or runtime_engine is None or admin_engine is None:
        runtime_disposed = await _dispose(runtime_engine)
        admin_disposed = await _dispose(admin_engine)
        _require(
            runtime_disposed and admin_disposed,
            "Race PostgreSQL setup failed and engine disposal failed or timed out",
        )
        pytest.fail(
            "Race PostgreSQL runtime/admin connection or actual role check failed", pytrace=False
        )

    database = RaceDatabase(
        runtime_sessions=async_sessionmaker(runtime_engine, expire_on_commit=False),
        runtime_engine=runtime_engine,
        admin_engine=admin_engine,
    )
    try:
        yield database
    finally:
        cleaned = await _cleanup(database)
        runtime_disposed = await _dispose(database.runtime_engine)
        admin_disposed = await _dispose(database.admin_engine)
        failures = []
        if not cleaned:
            failures.append("Scoped admin cleanup or committed zero-count readback failed")
        if not runtime_disposed or not admin_disposed:
            failures.append("Race PostgreSQL engine disposal failed or timed out")
        _require(not failures, "; ".join(failures))


async def _issue_synthetic_form(database: RaceDatabase, *, ttl: timedelta) -> SyntheticForm:
    subject_id = uuid4()
    owner_id = uuid4()

    async def issue(session: AsyncSession) -> tuple[SyntheticForm, bool | None]:
        async with session.begin():
            raw_token = await issue_form(
                session,
                subject_id=subject_id,
                purpose=FORM_PURPOSE,
                owner_type=FORM_OWNER_TYPE,
                owner_id=owner_id,
                ttl=ttl,
            )
            # Register before COMMIT, including an ambiguous/failed commit response.
            database.register(raw_token)
        result = await session.execute(
            text(
                "SELECT expires_at > now() "
                "FROM social.one_time_forms WHERE token_hash = :token_hash"
            ),
            {"token_hash": hash_token(raw_token)},
        )
        expires_in_future = result.scalar_one_or_none()
        return SyntheticForm(raw_token, subject_id, owner_id), expires_in_future

    form, expires_in_future = await _runtime_operation(database, issue)
    _require(expires_in_future is (ttl > timedelta(0)), "Synthetic form expiry state is incorrect")
    return form


async def _consume_pair(
    database: RaceDatabase, raw_token: str
) -> tuple[ConsumedForm | None, ConsumedForm | None]:
    barrier = asyncio.Barrier(2)
    identities: list[tuple[str, str, int]] = []
    committed: list[int] = []

    async def consume_once() -> ConsumedForm | None:
        async def consume(session: AsyncSession) -> tuple[ConsumedForm | None, int]:
            async with session.begin():
                connection = await session.connection()
                identity = (await connection.execute(IDENTITY_QUERY)).one()
                identities.append((identity[0], identity[1], identity[2]))
                if identity[0] != "sentinel_app" or identity[1] != "sentinel_app":
                    raise RuntimeError("contenders require the actual sentinel_app role")
                # Both transactions already hold independent connections before consuming.
                await barrier.wait()
                consumed = await consume_form(session, raw_token=raw_token, purpose=FORM_PURPOSE)
            # Reaching here proves COMMIT, including the losing transaction, succeeded.
            return consumed, identity[2]

        consumed, backend_pid = await _runtime_operation(database, consume)
        committed.append(backend_pid)
        return consumed

    tasks = [asyncio.create_task(consume_once()) for _ in range(2)]
    # Retrieve every child exception, even if a cancelled child finishes during teardown.
    joined = asyncio.gather(*tasks, return_exceptions=True)
    pair: tuple[ConsumedForm | None, ConsumedForm | None] | None = None
    try:
        done, _ = await asyncio.wait((joined,), timeout=PAIR_TIMEOUT)
        if done:
            first, second = joined.result()
            if not isinstance(first, BaseException) and not isinstance(second, BaseException):
                pair = (first, second)
    except BaseException:
        pair = None
    if pair is None:
        for task in tasks:
            task.cancel()
        drained = False
        try:
            done, _ = await asyncio.wait((joined,), timeout=CLOSE_TIMEOUT + QUERY_TIMEOUT)
            drained = bool(done)
        except BaseException:
            drained = False
        _require(drained, "Concurrent PostgreSQL consumers did not stop within the timeout")
        pytest.fail("Concurrent PostgreSQL consume operation failed or timed out", pytrace=False)

    _require(
        len(identities) == 2
        and all(current == login == "sentinel_app" for current, login, _ in identities),
        "Contenders did not both use current_user=session_user=sentinel_app",
    )
    _require(
        len({pid for _, _, pid in identities}) == 2,
        "Concurrent consumers did not use distinct PostgreSQL backend PIDs",
    )
    _require(len(committed) == 2, "Both concurrent consume transactions must commit")
    return pair


async def _consumed_state(database: RaceDatabase, raw_token: str) -> bool | None:
    # A fresh session/transaction observes only committed state; None means no row.
    async def read(session: AsyncSession) -> bool | None:
        result = await session.execute(
            text(
                "SELECT consumed_at IS NOT NULL "
                "FROM social.one_time_forms WHERE token_hash = :token_hash"
            ),
            {"token_hash": hash_token(raw_token)},
        )
        return result.scalar_one_or_none()

    return await _runtime_operation(database, read)


async def _consume_committed(database: RaceDatabase, raw_token: str) -> ConsumedForm | None:
    async def consume(session: AsyncSession) -> ConsumedForm | None:
        async with session.begin():
            consumed = await consume_form(session, raw_token=raw_token, purpose=FORM_PURPOSE)
        return consumed

    return await _runtime_operation(database, consume)


async def test_one_time_form_consume_race(race_database: RaceDatabase) -> None:
    winners = 0
    losers = 0
    consumed_after_commit = 0

    for _ in range(RACE_REPETITIONS):
        form = await _issue_synthetic_form(race_database, ttl=timedelta(minutes=5))
        pair = await _consume_pair(race_database, form.raw_token)

        pair_winners = [result for result in pair if result is not None]
        pair_losers = [result for result in pair if result is None]
        _require(
            len(pair_winners) == 1,
            "Race iteration must produce exactly one winner "
            f"(winners={len(pair_winners)}, losers={len(pair_losers)})",
        )
        _require(len(pair_losers) == 1, "Race iteration must produce exactly one loser")
        winner = pair_winners[0]
        _require(winner.subject_id == form.subject_id, "Winner subject binding is incorrect")
        _require(winner.owner_id == form.owner_id, "Winner owner binding is incorrect")
        _require(winner.owner_type == FORM_OWNER_TYPE, "Winner owner type is incorrect")
        _require(winner.purpose == FORM_PURPOSE, "Winner purpose is incorrect")
        consumed = await _consumed_state(race_database, form.raw_token)
        _require(consumed is True, "Committed consumed_at was not set")

        winners += len(pair_winners)
        losers += len(pair_losers)
        consumed_after_commit += 1

    print(
        "one-time-form race: "
        f"pairs={RACE_REPETITIONS} winners={winners} losers={losers} "
        f"consumed_after_commit={consumed_after_commit}"
    )


async def test_one_time_form_replay_and_expiry(race_database: RaceDatabase) -> None:
    form = await _issue_synthetic_form(race_database, ttl=timedelta(minutes=5))
    first_consume = await _consume_committed(race_database, form.raw_token)
    _require(first_consume is not None, "Initial consume did not win")
    consumed = await _consumed_state(race_database, form.raw_token)
    _require(consumed is True, "Initial consume did not persist consumed_at")

    replay = await _consume_committed(race_database, form.raw_token)
    _require(replay is None, "Replay consume unexpectedly succeeded")

    expired_form = await _issue_synthetic_form(race_database, ttl=timedelta(seconds=-1))
    expired_consume = await _consume_committed(race_database, expired_form.raw_token)
    _require(expired_consume is None, "Expired consume unexpectedly succeeded")
    expired_state = await _consumed_state(race_database, expired_form.raw_token)
    _require(expired_state is False, "Expired form must exist with NULL consumed_at")
    print("one-time-form replay/expiry: consumed replay and expired form were rejected")
