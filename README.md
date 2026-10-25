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
(see `docs/STATUS.md`). PR2-A is merged into `main` at `3700466`, PR2-B at `59a9da2`,
PR2-C at `57d7a85`, and PR2-D at `9466b0a`. Linux CI passed for PR2-D in the
[PR2-D run](https://github.com/AliRabiee2286/account-security-bot/actions/runs/39551172150)
with `P1-REDIS-WORKERS-XML tests=3 skipped=0 errors=0 failures=0` and
`Result: PARTIAL — 3 gates BLOCKED/NOT_RUN`. PR2-E is merged into `main` at `1262177`; Linux
CI passed the restore group in [run `40222607578`](https://github.com/AliRabiee2286/account-security-bot/actions/runs/40222607578).
The independent reviewer is still pending. Real Telegram delivery and two-person security review
remain open; local or CI PASS for one gate does not close the release gate.

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

Local and CI evidence for the updated group: connectivity **3 passed**, race **3 passed**,
full enabled suite **83 passed**, all with zero skips. Linux CI recorded:

```text
P1-RACE-XML tests=3 skipped=0 errors=0 failures=0
P1-RACE=PASS
Result: PARTIAL — 4 gates BLOCKED/NOT_RUN
```

See the [PR2-B Linux CI run](https://github.com/AliRabiee2286/account-security-bot/actions/runs/39372008697).
The overlap test
observes a real PostgreSQL `Lock` wait through `pg_stat_activity` before A commits; no guessed
sleep is used. A temporary unguarded consume copy makes both race shapes fail with two winners;
the copy is deleted and is not committed. Scope is PostgreSQL storage only, not HTTP, CSRF,
authorization, encryption, or end-to-end delivery. See
`tests/integration/README.md` and `evidence/PHASE1_EVIDENCE_TEMPLATE.md` for details.

### Runtime role privilege gate (PR2-C)

PR2-C is merged into `main` at `57d7a85`. Linux CI passed on implementation commit `554335d`:

```text
P1-ROLE-PRIVILEGES-XML tests=2 skipped=0 errors=0 failures=0
P1-ROLE=PASS
Result: PARTIAL — 4 gates BLOCKED/NOT_RUN
```

The independent role group checks the actual runtime
connection against `social.credentials`, `identity.sessions`, `identity.mfa_credentials`, and
`identity.approval_requests`: each allowed `SELECT` succeeds and each `DELETE` is rejected with
SQLSTATE `42501`. A separate admin catalog sweep covers all six application schemas and every
ordinary/partitioned table, rejecting runtime `DELETE`/`TRUNCATE`, audit `UPDATE`, schema
`CREATE`, unrestricted runtime role attributes, and missing `sentinel_app_role` membership.

See the [PR2-C Linux CI run](https://github.com/AliRabiee2286/account-security-bot/actions/runs/39386598021).
SEC-003 is confirmed by Linux CI; final closure remains pending independent review.
Local PostgreSQL 16 + Redis 7 disposable verification passed the two role tests with
`tests=2 skipped=0 errors=0 failures=0`, including temporary `DELETE` and `TRUNCATE` negative
controls and a trigger control that returned `P0001` rather than a privilege denial. The complete
local staging gate exited 0 with `P1-ROLE=PASS`, `P1-ROLE-PRIVILEGES` at two clean cases,
`P1-INTEGRATION` at three clean cases, and `P1-RACE` at three clean cases. The overall result
was `PARTIAL` because SECURITY, real webhook delivery, and restore remained blocked at that
stage; PR2-D adds the separate outbox-worker gate described below.

### Outbox worker/reclaim gate (PR2-D)

PR2-D is merged into `main` at `9466b0a`:

- `f4527e7` — `fix(outbox): cast interval parameter in reclaim_stuck` — the only product-code
  change; `CAST(:age AS interval)` fixes the real PostgreSQL reclaim failure.
- `f3f41ce` — two-worker, reclaim, and retry-timing integration tests plus the independent
  `P1-REDIS-WORKERS` gate.
- Linux CI recorded the independent outbox receipt; no push was performed from this workspace.

The local disposable gate recorded:

```text
P1-REDIS-WORKERS-XML tests=3 skipped=0 errors=0 failures=0
P1-REDIS-WORKERS=PASS scope=claim/lease/reclaim semantics; two concurrent in-process workers; lease ownership NOT enforced — stale-worker overwrite confirmed locally (SEC-004); test-only handler; no production handler
```

The first test used two concurrent `run_once()` workers, ten synthetic events, a local
test-only handler, and an untouched non-target row. The reclaim test seeded an old
`delivering` row with admin, reclaimed it without sleep, and delivered it once. The third test
covers the existing typed `mark_failed`/backoff interval path. Cleanup uses only
`sentinel_admin` and registered IDs.

Before the fix, the complete group was red: `tests=3`, `failures=1`, while the two-worker test
and mark-failed test passed. The sanitized receipt is in
`evidence/PR2-D-RED-RECLAIM.md`. A temporary claim mutation without the status predicate made
the two-worker test fail by repeatedly claiming work; the mutation was external and deleted.

The SEC-004 experiment confirmed **YES**: after reclaim, an old paused worker can still execute
`mark_delivered` while a new worker holds the replacement lease, changing the row to
`delivered` before the new worker finishes. Lease ownership is explicitly outside this gate and
remains a release blocker for real providers.

The initial read-only timed-SQL inventory found the failing untyped `now() - :age` in
`app/entrypoints/workers/outbox_runner.py:27-28` and the already explicit
`now() + CAST(:delay AS interval)` in `app/core/outbox_dispatch.py:78-83`. No other app raw SQL
combining `now()` with a timed parameter was found. See `task_plan.md` TEST-002 and
`docs/NEXT_SESSION.md` for the boundary and next package.

### Logical restore gate (PR2-E)

PR2-E is merged into `main` at `1262177` (implementation `e3e03d7`). It adds one independent
integration module, one `P1-RESTORE` staging-gate group, and the CI container-name variable;
`app/` and `migrations/` were not changed. The scope is deliberately limited to a logical
PostgreSQL 16 `pg_dump --format=custom` / `pg_restore` round trip inside the disposable
container: synthetic data, table-set equality, row counts, md5 digests, migration head
`0007`, no forbidden privileges after restore (DELETE/TRUNCATE; audit UPDATE); allowed privileges
not compared (TEST-005), audit-trigger presence, and in-container dump cleanup. It
does not claim encrypted backup, PITR, or a production backup process.

The local full gate passed with:

```text
P1-RESTORE-DIAGNOSTIC=pytest_exit=0 xml_exit=0
P1-RESTORE-XML tests=2 skipped=0 errors=0 failures=0
P1-RESTORE=PASS
STAGING_GATE_STATUS=0
```

Linux CI also passed the independent restore group:

```text
P1-RESTORE-XML tests=2 skipped=0 errors=0 failures=0
P1-RESTORE=PASS
Result: PARTIAL — 2 gates BLOCKED/NOT_RUN
```

See the [PR2-E Linux CI run](https://github.com/AliRabiee2286/account-security-bot/actions/runs/40222607578).

The three disposable negative controls also passed: changing a restored row produced an md5
mismatch with equal counts, deleting a restored row produced a count mismatch, and a temporary
`DELETE` grant to `sentinel_app_role` was detected by the no forbidden privileges after restore
check (DELETE/TRUNCATE; audit UPDATE); allowed privileges not compared (TEST-005), and revoked. The
append-only synthetic audit row is intentionally retained until the disposable database is
destroyed; it is not cleanup data. Independent review remains pending.

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
