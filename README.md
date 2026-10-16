# sentinel

A modular bot for company account security and leak response. 500+ employees voluntarily
centralize their social accounts (Instagram, X, Telegram) on company mailboxes. If sensitive
company data leaks, the bot detects and removes it fast, then secures the accounts.

## Quick start (dev)

```bash
# Install from the reviewed lockfile
uv sync --frozen
pre-commit install

# Run (PostgreSQL and Redis must be running; Docker Compose helps)
docker compose up -d db redis
uv run alembic upgrade head
uv run uvicorn app.entrypoints.api.main:app --reload &
uv run arq app.entrypoints.workers.settings.WorkerSettings &
# Test: curl http://localhost:8000/healthz
```

## Structure

```
app/
  core/              # shared: logging, crypto, IDs, DB, RBAC, errors
  modules/           # domain logic, one per business concern
    identity/        # employees, roles, permissions (RBAC with inheritance)
    audit/           # append-only event log (tamper-evident hash chain)
    mailboxes/       # email accounts (Phase 2; scaffolded)
    social/          # Instagram, X, Telegram accounts (Phase 3)
    incidents/       # leak detection and response (Phase 4)
    alerts/          # rules and notifications (Phase 5)
  adapters/          # pluggable external integrations
    email/           # Atomic Mail, custom JMAP server, etc.
    social/          # Instagram API, X API, Telegram Bot API
    scanning/        # OCR, content detection
    keys/            # local KMS, Vault, etc.
  entrypoints/       # HTTP and bot entry points (thin handlers)
    api/             # FastAPI: Telegram webhook, health, forms
    bot/             # aiogram: message handlers
    admin/           # SQLAdmin panel (Phase 5)
    workers/         # arq background jobs (Phase 3+)
docs/
  adr/               # Architecture Decision Records
migrations/          # database schema (Alembic)
tests/               # unit and integration tests
```

---
**Built with:** Python 3.12, FastAPI, aiogram 3, SQLAlchemy 2, PostgreSQL 16, Redis 7, Docker.

## Current delivery gate

The offline foundation gate is green: the project has a checked-in `uv.lock`, strict typing,
Ruff, import boundaries, unit tests, import smoke, migration/static validators, and offline
security smoke. This does **not** make the project production-ready. Phase 1 remains
**blocked/pre-staging** until an environment with Docker/Compose, PostgreSQL 16, Redis 7 and
the test Telegram bot produces runtime evidence for empty-database migration, two-worker
concurrency, webhook smoke, backup restore, CI and two-person security review.

Run the complete environment gate only from `docs/STAGING_RUNBOOK.md`. Runtime uses
`DATABASE_URL` with the least-privileged `sentinel_app` role; Alembic uses the separate
privileged `MIGRATION_DATABASE_URL`.

## Authentication gate

OAuth PKCE primitives, signed Telegram Mini App `initData` validation, and an explicit
`AuthContext` boundary now exist. Registration creates only a `pending` employee. Incident and
privileged endpoints remain fail-closed until Telegram-linked session issuance and phishing-
resistant WebAuthn are installed and tested in staging. Do not replace this with a body/header
employee ID shortcut.

## Phase 2 identity rule

Telegram user ID proves message origin, not employment. Registration remains `pending`; admin
approval is required. The HTTP registration bootstrap accepts only a fresh, HMAC-validated
Telegram Mini App `initData`; it never accepts a client-supplied Telegram ID as proof.

## Offline checks versus staging evidence

`uv run pytest -q` intentionally skips integration tests unless `RUN_INTEGRATION=1` is set.
Static/offline PASS means the code is ready to take to staging; it does not satisfy the Phase 1
release gate. Never add real credentials, employee data or production provider accounts to this
workspace.
