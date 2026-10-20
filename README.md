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
security smoke. This does **not** make the project production-ready. Phase 1 is **PARTIAL**
(see `docs/STATUS.md`). PR2-A is merged into `main` at `3700466`. PR2-B adds locally verified
one-time-form races; its Linux CI evidence and independent review are still pending. Real
Telegram delivery, two-worker outbox/reclaim, restore, and two-person security review remain
open; local PASS does not close the release gate.

Run the complete environment gate only from `docs/STAGING_RUNBOOK.md`. Runtime uses
`DATABASE_URL` with the least-privileged `sentinel_app` role; Alembic uses the separate
privileged `MIGRATION_DATABASE_URL`.

### One-time-form race gate (PR2-B)

After provisioning disposable services and migrating as admin, run the groups independently:

```bash
RUN_INTEGRATION=1 uv run pytest -q \
  tests/integration/test_gate_contract.py tests/integration/test_runtime_connectivity.py
RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_one_time_form_race.py
```

The race test executes 20 concurrent pairs, each with a fresh synthetic form. Both runtime
transactions commit on distinct PostgreSQL backend connections; every pair must have exactly
one winner and one loser, with committed `consumed_at` set. The second test rejects replay and
expired forms. Admin cleanup deletes only that test's registered hashes and verifies no rows
remain; runtime DELETE is intentionally forbidden.

Local evidence for the updated group: connectivity **3 passed**, race **3 passed**, full
enabled suite **83 passed**, all with zero skips. The overlap test
observes a real PostgreSQL `Lock` wait through `pg_stat_activity` before A commits; no guessed
sleep is used. A temporary unguarded consume copy makes both race shapes fail with two winners;
the copy is deleted and is not committed. Scope is PostgreSQL storage only, not HTTP, CSRF,
authorization, encryption, or end-to-end delivery. See
`tests/integration/README.md` and `evidence/PHASE1_EVIDENCE_TEMPLATE.md` for details.

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
