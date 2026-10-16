#!/usr/bin/env bash
set -euo pipefail
# Run only in a disposable/staging environment with .env configured.
: "${DATABASE_URL:?DATABASE_URL is required}"
: "${MIGRATION_DATABASE_URL:?MIGRATION_DATABASE_URL is required}"
: "${REDIS_URL:?REDIS_URL is required}"
: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN is required}"
: "${TELEGRAM_WEBHOOK_SECRET:?TELEGRAM_WEBHOOK_SECRET is required}"
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run lint-imports
uv run pytest -q
uv run alembic upgrade head
uv run pytest -q tests/integration
