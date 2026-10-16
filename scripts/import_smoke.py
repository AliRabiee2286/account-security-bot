"""Import every package module and report all failures without secret values."""

from __future__ import annotations

import importlib
import os
import pkgutil
import sys
from collections.abc import Iterable
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _safe_environment() -> None:
    """Supply harmless values when the smoke check is run without a .env file."""

    defaults = {
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
        # Avoid Pydantic plugin discovery, which is unnecessary for this offline check.
        "PYDANTIC_DISABLE_PLUGINS": "1",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)
    # This check is offline-only; never allow caller configuration to re-enable plugins.
    os.environ["PYDANTIC_DISABLE_PLUGINS"] = "1"


def _module_names(package_name: str) -> Iterable[str]:
    package = importlib.import_module(package_name)
    yield package_name
    if hasattr(package, "__path__"):
        pending = [(package.__path__, package.__name__ + ".")]
        while pending:
            search_path, prefix = pending.pop()
            for module in pkgutil.iter_modules(search_path, prefix):
                yield module.name
                if module.ispkg:
                    child_path = next(
                        (
                            path
                            for path in search_path
                            if (Path(path) / module.name.rsplit(".", 1)[-1]).is_dir()
                        ),
                        None,
                    )
                    if child_path is not None:
                        pending.append(
                            (
                                [str(Path(child_path) / module.name.rsplit(".", 1)[-1])],
                                module.name + ".",
                            )
                        )


def main(package_name: str = "app") -> int:
    root = _project_root()
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    _safe_environment()

    failures: list[tuple[str, str]] = []
    modules = sorted(set(_module_names(package_name)))
    for module_name in modules:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            failures.append((module_name, type(exc).__name__))

    if failures:
        print(f"import smoke: FAIL ({len(failures)} module failures)")
        for module_name, exception_type in failures:
            print(f"{module_name}: {exception_type}")
        return 1

    print(f"import smoke: PASS ({len(modules)} modules)")
    for module_name in modules:
        print(module_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
