"""Contract tests for locked release and staging configuration."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _validator_workspace(tmp_path: Path, env_text: str | None = None) -> Path:
    (tmp_path / "scripts").mkdir()
    for relative_path in (
        "scripts/validate_config.py",
        "docker-compose.yml",
        "Dockerfile",
        "uv.lock",
    ):
        source = PROJECT_ROOT / relative_path
        destination = tmp_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    shutil.copy2(PROJECT_ROOT / ".env.example", tmp_path / ".env.example")
    if env_text is not None:
        (tmp_path / ".env.example").write_text(env_text, encoding="utf-8")
    return tmp_path


def _run_validator(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/validate_config.py"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_validator_accepts_locked_config() -> None:
    result = _run_validator(PROJECT_ROOT)

    assert result.returncode == 0, result.stderr or result.stdout


def test_validator_requires_migration_database_url(tmp_path: Path) -> None:
    env_text = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    env_text = "\n".join(
        line for line in env_text.splitlines() if not line.startswith("MIGRATION_DATABASE_URL=")
    )

    result = _run_validator(_validator_workspace(tmp_path, env_text))

    assert result.returncode != 0
    assert "MIGRATION_DATABASE_URL" in result.stderr or "MIGRATION_DATABASE_URL" in result.stdout


@pytest.mark.parametrize(
    "replacement",
    [
        ("MIGRATION_DATABASE_URL=postgresql+asyncpg://sentinel_admin:", ""),
        (
            "MIGRATION_DATABASE_URL=postgresql+asyncpg://sentinel_admin:CHANGE_ME@db:5432/sentinel",
            "MIGRATION_DATABASE_URL=postgresql+asyncpg://sentinel_app:CHANGE_ME@db:5432/sentinel",
        ),
    ],
)
def test_validator_rejects_removed_runtime_migration_split(
    tmp_path: Path, replacement: tuple[str, str]
) -> None:
    env_text = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    env_text = env_text.replace(*replacement)

    result = _run_validator(_validator_workspace(tmp_path, env_text))

    assert result.returncode != 0
    assert "migration" in (result.stderr + result.stdout).lower()
