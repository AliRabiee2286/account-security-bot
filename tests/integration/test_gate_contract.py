"""Placeholder contract for the staging gate. No fake pass: skipped until services are present."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1", reason="requires disposable PostgreSQL and Redis staging"
)


def test_integration_environment_is_explicit():
    assert os.getenv("DATABASE_URL")
    assert os.getenv("REDIS_URL")
