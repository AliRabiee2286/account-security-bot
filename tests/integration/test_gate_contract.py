"""Explicit environment contract for the real disposable integration gate."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1", reason="requires disposable PostgreSQL and Redis staging"
)


def test_integration_environment_is_explicit() -> None:
    required = ("DATABASE_URL", "MIGRATION_DATABASE_URL", "REDIS_URL")
    missing = [name for name in required if not os.getenv(name, "").strip()]
    # Only names reach assertion introspection, never values from the environment.
    assert not missing, "Missing integration environment: " + ", ".join(missing)
