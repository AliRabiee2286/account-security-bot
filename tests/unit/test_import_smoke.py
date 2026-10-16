"""Exercise the standalone import check in fresh interpreters, without services."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "import_smoke.py"


def test_import_smoke_works_outside_project_with_hostile_environment(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "APP_ENV=prod\nTELEGRAM_BOT_TOKEN=invalid\nTELEGRAM_WEBHOOK_SECRET=short\n",
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "APP_ENV": "dev",
        "DATABASE_URL": "postgresql+asyncpg://sentinel_app:offline_dummy@127.0.0.1:1/sentinel",
        "MIGRATION_DATABASE_URL": "postgresql+asyncpg://sentinel_admin:offline_dummy@127.0.0.1:1/sentinel",
        "REDIS_URL": "redis://:offline_dummy@127.0.0.1:1/0",
        "TELEGRAM_BOT_TOKEN": "123456789:offline_dummy_token_never_use",
        "TELEGRAM_WEBHOOK_SECRET": "offline_dummy_webhook_secret_0000000000",
        "PUBLIC_BASE_URL": "https://offline.invalid",
        "MODULE_MAILBOXES_ENABLED": "true",
        "MODULE_SOCIAL_ENABLED": "true",
        "MODULE_INCIDENTS_ENABLED": "true",
    }
    result = subprocess.run(  # noqa: S603 - executable and arguments are fixed test inputs
        [sys.executable, str(SCRIPT)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "import smoke:" in result.stdout
    assert "PASS" in result.stdout
    assert "app.entrypoints.api.main" in result.stdout
    assert "app.entrypoints.workers.settings" in result.stdout


def test_import_smoke_reports_all_failures_without_exception_secrets(tmp_path: Path) -> None:
    package = tmp_path / "smoke_fixture"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "first.py").write_text("raise RuntimeError('DO-NOT-PRINT-TOKEN')", encoding="utf-8")
    (package / "second.py").write_text("raise ImportError('DO-NOT-PRINT-TOKEN')", encoding="utf-8")
    (package / "healthy.py").write_text("value = 1", encoding="utf-8")
    broken_package = package / "broken"
    broken_package.mkdir()
    (broken_package / "__init__.py").write_text(
        "raise ValueError('DO-NOT-PRINT-TOKEN')", encoding="utf-8"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from scripts.import_smoke import main; raise SystemExit(main('smoke_fixture'))",
        ],
        cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 1
    assert "smoke_fixture.first: RuntimeError" in result.stdout
    assert "smoke_fixture.second: ImportError" in result.stdout
    assert "smoke_fixture.broken: ValueError" in result.stdout
    assert "DO-NOT-PRINT-TOKEN" not in result.stdout + result.stderr
