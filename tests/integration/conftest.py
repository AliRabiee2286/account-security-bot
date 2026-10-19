"""Shared real-service fixtures for the disposable integration gate."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import asyncpg
import pytest
from redis.asyncio import Redis
from sqlalchemy.engine import make_url

CONNECT_TIMEOUT = 5
CLEANUP_TIMEOUT = 3
REQUIRED_ENVIRONMENT = ("DATABASE_URL", "MIGRATION_DATABASE_URL", "REDIS_URL")


class _IntegrationReportGuard:
    """An enabled gate must execute tests without any skipped reports."""

    def __init__(self) -> None:
        self.call_reports = 0
        self.skipped = False

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when == "call":
            self.call_reports += 1
        self.skipped |= report.skipped

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        self.skipped |= report.skipped

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        if session.exitstatus == pytest.ExitCode.OK and (self.skipped or not self.call_reports):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_configure(config: pytest.Config) -> None:
    if os.getenv("RUN_INTEGRATION") == "1":
        config.pluginmanager.register(_IntegrationReportGuard(), "integration-report-guard")


@dataclass(frozen=True)
class IntegrationEnvironment:
    database_url: str = field(repr=False)
    redis_url: str = field(repr=False)


def _integration_environment() -> IntegrationEnvironment:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("requires RUN_INTEGRATION=1")

    missing = [name for name in REQUIRED_ENVIRONMENT if not os.getenv(name, "").strip()]
    if missing:
        pytest.fail("Missing integration environment: " + ", ".join(missing), pytrace=False)
    return IntegrationEnvironment(
        database_url=os.environ["DATABASE_URL"], redis_url=os.environ["REDIS_URL"]
    )


@pytest.fixture(scope="session")
def integration_environment() -> IntegrationEnvironment:
    return _integration_environment()


@pytest.fixture
async def postgres_connection(
    integration_environment: IntegrationEnvironment,
) -> AsyncIterator[asyncpg.Connection]:
    connection = None
    failed = False
    try:
        url = make_url(integration_environment.database_url)
        if url.drivername not in {"postgres", "postgresql", "postgresql+asyncpg"}:
            raise ValueError("unsupported runtime PostgreSQL driver")
        if url.username != "sentinel_app":
            raise ValueError("runtime PostgreSQL must use sentinel_app")
        # Parse and re-render instead of replacing text inside an encoded password.
        dsn = url.set(drivername="postgresql").render_as_string(hide_password=False)
        async with asyncio.timeout(CONNECT_TIMEOUT):
            connection = await asyncpg.connect(
                dsn=dsn,
                timeout=CONNECT_TIMEOUT,
                command_timeout=CONNECT_TIMEOUT,
            )
    except Exception:
        failed = True

    # Fail outside the handler so driver exceptions (which may contain DSNs) are not chained.
    if failed or connection is None:
        pytest.fail("PostgreSQL runtime connection/configuration failed", pytrace=False)

    try:
        yield connection
    finally:
        close_failed = False
        try:
            # asyncpg aborts the connection if graceful close fails or times out.
            await connection.close(timeout=CLEANUP_TIMEOUT)
        except Exception:
            close_failed = True
        if close_failed:
            pytest.fail("PostgreSQL connection cleanup failed", pytrace=False)


async def _close_redis(client: Redis) -> bool:
    failed = False
    try:
        async with asyncio.timeout(CLEANUP_TIMEOUT):
            await client.aclose(close_connection_pool=True)
    except Exception:
        failed = True
    return not failed


@pytest.fixture
async def redis_client(
    integration_environment: IntegrationEnvironment,
) -> AsyncIterator[Redis]:
    client = None
    failed = False
    try:
        # URL parsing and construction can fail before ping, so guard both.
        async with asyncio.timeout(CONNECT_TIMEOUT):
            client = Redis.from_url(
                integration_environment.redis_url,
                decode_responses=True,
                socket_connect_timeout=CONNECT_TIMEOUT,
                socket_timeout=CONNECT_TIMEOUT,
            )
            await client.ping()
    except Exception:
        failed = True

    if failed or client is None:
        if client is not None:
            await _close_redis(client)
        pytest.fail("Redis connection/configuration failed", pytrace=False)

    try:
        yield client
    finally:
        if not await _close_redis(client):
            pytest.fail("Redis client cleanup failed", pytrace=False)
