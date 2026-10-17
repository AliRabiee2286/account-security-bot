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

    assert check["runs-on"] == "ubuntu-24.04"
    assert check["timeout-minutes"] == 20
    assert workflow["permissions"] == {"contents": "read"}

    steps = check["steps"]
    credential_step = next(
        step for step in steps if step.get("name") == "Generate disposable CI credentials"
    )
    credential_run = credential_step["run"]
    assert credential_run.count("secrets.token_urlsafe(24)") == 4
    assert credential_run.count("secrets.token_urlsafe(32)") == 1
    assert 'postgres_admin_password="$(python3 -c' in credential_run
    assert 'sentinel_app_password="$(python3 -c' in credential_run
    assert 'redis_password="$(python3 -c' in credential_run
    assert 'telegram_webhook_secret="$(python3 -c' in credential_run
    assert 'telegram_bot_token="$(python3 -c' in credential_run
    assert 'public_base_url="https://ci-${GITHUB_RUN_ID}.invalid"' in credential_run
    assert credential_run.count("::add-mask::") == 6
    assert "GITHUB_ENV" in credential_run
    for variable in ("telegram_webhook_secret", "telegram_bot_token", "public_base_url"):
        assert f"printf '::add-mask::%s\\n' \"${variable}\"" in credential_run
    assert credential_run.rfind("::add-mask::") < credential_run.find("GITHUB_ENV")
    for key, variable in (
        ("TELEGRAM_WEBHOOK_SECRET", "telegram_webhook_secret"),
        ("TELEGRAM_BOT_TOKEN", "telegram_bot_token"),
        ("PUBLIC_BASE_URL", "public_base_url"),
    ):
        assert f"printf '{key}=%s\\n' \"${variable}\"" in credential_run
    expected_dsn_lines = (
        (
            r"printf 'DATABASE_URL=postgresql+asyncpg://sentinel_app:%s@"
            r"127.0.0.1:5432/sentinel\n' "
            '"$sentinel_app_password"'
        ),
        (
            r"printf 'MIGRATION_DATABASE_URL=postgresql+asyncpg://sentinel_admin:%s@"
            r"127.0.0.1:5432/sentinel\n' "
            '"$postgres_admin_password"'
        ),
        (
            r"printf 'PSQL_RUNTIME_DSN=postgresql://sentinel_app:%s@"
            r"127.0.0.1:5432/sentinel\n' "
            '"$sentinel_app_password"'
        ),
        (
            r"printf 'PSQL_ADMIN_DSN=postgresql://sentinel_admin:%s@"
            r"127.0.0.1:5432/sentinel\n' "
            '"$postgres_admin_password"'
        ),
    )
    for expected_line in expected_dsn_lines:
        assert expected_line in credential_run

    assert (
        r"printf 'DATABASE_URL=postgresql+asyncpg://sentinel_app:%s@"
        r"127.0.0.1:5432/sentinel\n' "
        '"$postgres_admin_password"'
    ) not in credential_run
    assert (
        r"printf 'MIGRATION_DATABASE_URL=postgresql+asyncpg://sentinel_admin:%s@"
        r"127.0.0.1:5432/sentinel\n' "
        '"$sentinel_app_password"'
    ) not in credential_run
    assert (
        r"printf 'PSQL_RUNTIME_DSN=postgresql://sentinel_app:%s@"
        r"127.0.0.1:5432/sentinel\n' "
        '"$postgres_admin_password"'
    ) not in credential_run
    assert (
        r"printf 'PSQL_ADMIN_DSN=postgresql://sentinel_admin:%s@"
        r"127.0.0.1:5432/sentinel\n' "
        '"$sentinel_app_password"'
    ) not in credential_run

    postgres_step = next(
        step for step in steps if step.get("name") == "Start disposable PostgreSQL"
    )
    assert "--env POSTGRES_USER=sentinel_admin" in postgres_step["run"]
    redis_step = next(step for step in steps if step.get("name") == "Start disposable Redis")
    assert "--requirepass" in redis_step["run"]

    workflow_text = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for fixed_password in ("sentinel_app_ci", "sentinel_admin_ci", "redis_ci_password"):
        assert fixed_password not in workflow_text
    assert "TELEGRAM_BOT_TOKEN=123456789:" not in workflow_text
    assert "TELEGRAM_WEBHOOK_SECRET=offline_dummy" not in workflow_text

    gate_step = next(step for step in steps if step.get("name") == "Run staging gate")
    assert gate_step["run"] == "bash scripts/staging_gate.sh"

    workflow_runs = "\n".join(str(step.get("run", "")) for step in steps)
    for gate_command in ("alembic", "pytest", "ruff", "mypy", "lint-imports"):
        assert gate_command not in workflow_runs
