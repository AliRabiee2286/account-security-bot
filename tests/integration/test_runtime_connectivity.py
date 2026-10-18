"""Real PostgreSQL and Redis round-trip checks for disposable staging."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import asyncpg
import pytest
from redis.asyncio import Redis

QUERY_TIMEOUT = 5
CLEANUP_TIMEOUT = 3


async def test_postgresql_synthetic_write_read(
    postgres_connection: asyncpg.Connection,
) -> None:
    synthetic_id = uuid4()
    event_type = "pr2a.connectivity"
    request_id = f"pr2a-{uuid4()}"
    payload = {"probe": "postgresql", "synthetic": True}

    transaction = None
    failure = None
    stage = "migrated outbox/runtime role check"
    try:
        async with asyncio.timeout(QUERY_TIMEOUT):
            environment = await postgres_connection.fetchrow(
                "SELECT current_user, session_user, "
                "to_regclass('core.outbox') IS NOT NULL AS outbox_exists"
            )
            assert environment is not None
            assert environment["current_user"] == "sentinel_app"
            assert environment["session_user"] == "sentinel_app"
            assert environment["outbox_exists"] is True

            stage = "synthetic write/read"
            transaction = postgres_connection.transaction()
            await transaction.start()
            await postgres_connection.execute(
                """
                INSERT INTO core.outbox (id, event_type, payload, request_id)
                VALUES ($1, $2, $3::jsonb, $4)
                """,
                synthetic_id,
                event_type,
                json.dumps(payload, separators=(",", ":")),
                request_id,
            )
            row = await postgres_connection.fetchrow(
                "SELECT id, event_type, payload, request_id FROM core.outbox WHERE id = $1",
                synthetic_id,
            )

            assert row is not None
            assert row["id"] == synthetic_id
            assert row["event_type"] == event_type
            assert json.loads(row["payload"]) == payload
            assert row["request_id"] == request_id
    except Exception:
        failure = f"PostgreSQL integration {stage} failed"
    finally:
        if transaction is not None:
            try:
                async with asyncio.timeout(CLEANUP_TIMEOUT):
                    await transaction.rollback()
            except Exception:
                failure = "PostgreSQL synthetic transaction rollback failed"

    if failure is not None:
        pytest.fail(failure, pytrace=False)

    # A successful probe must not leave a pending event for a real worker to dispatch.
    failed = False
    try:
        async with asyncio.timeout(QUERY_TIMEOUT):
            assert not await postgres_connection.fetchval(
                "SELECT EXISTS (SELECT 1 FROM core.outbox WHERE id = $1)", synthetic_id
            )
    except Exception:
        failed = True
    if failed:
        pytest.fail("PostgreSQL synthetic rollback verification failed", pytrace=False)


async def test_redis_synthetic_set_get_delete(redis_client: Redis) -> None:
    key = f"pr2a:connectivity:{uuid4()}"
    value = f"synthetic-{uuid4()}"

    failure = None
    try:
        async with asyncio.timeout(QUERY_TIMEOUT):
            assert await redis_client.set(key, value, ex=30)
            assert await redis_client.get(key) == value
            assert await redis_client.delete(key) == 1
            assert await redis_client.get(key) is None
    except Exception:
        failure = "Redis synthetic SET/GET/delete failed"
    finally:
        try:
            async with asyncio.timeout(CLEANUP_TIMEOUT):
                await redis_client.delete(key)
        except Exception:
            failure = "Redis synthetic key cleanup failed (TTL remains bounded)"
    if failure is not None:
        pytest.fail(failure, pytrace=False)
