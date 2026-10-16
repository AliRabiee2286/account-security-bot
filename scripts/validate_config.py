"""Ensure the checked-in deployment configuration is safe and reproducible."""

from __future__ import annotations

from pathlib import Path


def _env_assignments(text: str) -> dict[str, str]:
    assignments: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        assignments[key.strip()] = value.strip()
    return assignments


def _validate_environment(root: Path) -> None:
    env_text = (root / ".env.example").read_text(encoding="utf-8")
    assignments = _env_assignments(env_text)
    required_keys = {
        "TELEGRAM_WEBHOOK_SECRET",
        "MASTER_KEY_FILE",
        "DATABASE_URL",
        "MIGRATION_DATABASE_URL",
        "REDIS_PASSWORD",
        "REDIS_URL",
    }
    missing_keys = sorted(required_keys - assignments.keys())
    if missing_keys:
        raise SystemExit(f"config template missing required keys: {', '.join(missing_keys)}")

    if "localhost" in env_text:
        raise SystemExit("example config must use service names, not localhost")
    if "MODULE_" not in env_text:
        raise SystemExit("config template must include module feature flags")

    database_url = assignments["DATABASE_URL"]
    migration_database_url = assignments["MIGRATION_DATABASE_URL"]
    if not database_url.startswith("postgresql+asyncpg://sentinel_app:"):
        raise SystemExit("runtime DATABASE_URL must use the sentinel_app role")
    if not migration_database_url.startswith("postgresql+asyncpg://sentinel_admin:"):
        raise SystemExit("migration MIGRATION_DATABASE_URL must use the sentinel_admin role")
    if database_url == migration_database_url:
        raise SystemExit(
            "runtime DATABASE_URL and migration MIGRATION_DATABASE_URL must remain separate"
        )
    if not assignments["REDIS_URL"].startswith("redis://:CHANGE_ME@redis:"):
        raise SystemExit("example REDIS_URL must use the private redis service")


def _validate_compose(root: Path) -> None:
    compose_text = (root / "docker-compose.yml").read_text(encoding="utf-8")
    if "SENTINEL_APP_PASSWORD" not in compose_text:
        raise SystemExit("Compose must provision the runtime database password")
    if "POSTGRES_USER: sentinel_admin" not in compose_text:
        raise SystemExit("Compose must use sentinel_admin for migrations")
    if "--requirepass" not in compose_text:
        raise SystemExit("Compose must require a Redis password")
    if "docker/postgres/init" not in compose_text:
        raise SystemExit("Compose must provision the runtime database role")


def _validate_frozen_install(root: Path) -> None:
    dockerfile_text = (root / "Dockerfile").read_text(encoding="utf-8")
    if "COPY pyproject.toml uv.lock ./" not in dockerfile_text:
        raise SystemExit("Dockerfile must copy uv.lock before dependency installation")
    if "uv sync --frozen --no-dev" not in dockerfile_text:
        raise SystemExit("Dockerfile must install dependencies with uv sync --frozen --no-dev")

    staging_gate_text = (root / "scripts" / "staging_gate.sh").read_text(encoding="utf-8")
    if "uv sync --frozen" not in staging_gate_text:
        raise SystemExit("staging gate must use uv sync --frozen")

    lock_path = root / "uv.lock"
    if not lock_path.is_file():
        raise SystemExit("uv.lock is required for reproducible installs")


def validate_config(root: Path = Path(".")) -> None:
    _validate_environment(root)
    _validate_compose(root)
    _validate_frozen_install(root)


if __name__ == "__main__":
    validate_config()
    print("config template static check: ok")
