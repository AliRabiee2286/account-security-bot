"""Contract tests for Compose and CI deployment configuration."""

from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_yaml(relative_path: str) -> dict[str, object]:
    document = yaml.safe_load((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_compose_redis_command_is_yaml_safe_and_password_protected() -> None:
    compose = _read_yaml("docker-compose.yml")
    services = compose["services"]
    assert isinstance(services, dict)

    redis = services["redis"]
    assert isinstance(redis, dict)
    command = redis["command"]
    assert isinstance(command, list)
    assert command[:2] == ["sh", "-c"]
    assert "--requirepass" in command[2]
    assert "$$REDIS_PASSWORD" in command[2]


def test_compose_keeps_database_and_redis_private() -> None:
    compose = _read_yaml("docker-compose.yml")
    services = compose["services"]
    assert isinstance(services, dict)

    for service_name in ("db", "redis"):
        service = services[service_name]
        assert isinstance(service, dict)
        assert "ports" not in service


def test_api_and_worker_wait_for_healthy_database_and_redis() -> None:
    compose = _read_yaml("docker-compose.yml")
    services = compose["services"]
    assert isinstance(services, dict)

    for service_name in ("api", "worker"):
        service = services[service_name]
        assert isinstance(service, dict)
        depends_on = service["depends_on"]
        assert isinstance(depends_on, dict)
        assert depends_on["db"]["condition"] == "service_healthy"
        assert depends_on["redis"]["condition"] == "service_healthy"


def test_ci_uses_separate_runtime_and_migration_roles() -> None:
    workflow = _read_yaml(".github/workflows/ci.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    check = jobs["check"]
    assert isinstance(check, dict)

    services = check["services"]
    assert isinstance(services, dict)
    postgres = services["postgres"]
    assert isinstance(postgres, dict)
    assert postgres["env"]["POSTGRES_USER"] == "sentinel_admin"
    assert "redis" in services

    job_env = check["env"]
    assert job_env["DATABASE_URL"].startswith("postgresql+asyncpg://sentinel_app:")
    assert job_env["MIGRATION_DATABASE_URL"].startswith("postgresql+asyncpg://sentinel_admin:")
    assert job_env["REDIS_URL"].startswith("redis://:")

    steps = check["steps"]
    role_setup = next(step for step in steps if step.get("name") == "Create runtime database role")
    assert "sentinel_app" in role_setup["run"]
    migration_step = next(step for step in steps if step.get("name") == "Run migrations")
    assert migration_step["env"]["MIGRATION_DATABASE_URL"] == job_env["MIGRATION_DATABASE_URL"]
