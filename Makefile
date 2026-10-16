.PHONY: install check test migrate dev
install:
	uv sync
check:
	uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run lint-imports

test:
	uv run pytest -q
migrate:
	uv run alembic upgrade head
dev:
	docker compose up -d db redis
