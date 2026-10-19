# Phase 1 Staging Evidence

Run ID: ____________________
Commit: ____________________
Environment owner: ____________________
Reviewer 1: ____________________
Reviewer 2: ____________________

Result values: `PASS` means the exact gate ran and evidence is attached; `BLOCKED` means the
runtime prerequisite or evidence is missing; `NOT RUN` means the operator did not attempt it.
Offline/static PASS is informative and does not close Phase 1.

| Gate | Command / test | Result | Evidence link | Reviewer |
|---|---|---|---|---|
| P1-DB | `alembic upgrade head` from empty DB | BLOCKED | | |
| P1-REDIS | two-worker outbox + stuck reclaim | BLOCKED | | |
| P1-CI | uv sync, ruff, mypy, import-linter, pytest | BLOCKED | | |
| P1-RACE | concurrent form consume, exactly one winner | BLOCKED | | |
| P1-WEBHOOK | invalid secret 403, valid secret 200 | BLOCKED | | |
| P1-RESTORE | encrypted backup restore and checksum | BLOCKED | | |
| P1-SECURITY | review S-011..S-022 applicable controls | BLOCKED | | |
| P1-OFFLINE | lock, compile, unit, Ruff, mypy, import boundaries, offline smoke | PASS (workspace only) | | |

## Release decision

- [ ] PASS: all rows have evidence and two reviewers
- [ ] BLOCKED: at least one row lacks runtime evidence

No production credentials or real employee data may be used for this run.
| P1-LOCK | reviewed `uv.lock` + frozen install | BLOCKED | | |

## Recorded CI runs

| Run | Commit | Result | Cause | Executed before failure | Not run after failure | Evidence / reviewers |
|---|---|---|---|---|---|---|
| #2 | `d9df3ec` | **FAIL** | `tests/unit/test_deployment_config.py::test_ci_uses_separate_runtime_and_migration_roles` raised `KeyError: 'services'`; the test assumed the removed GitHub service-container design. | Service health; lock check; Ruff; format check; mypy; import-linter; 72 unit tests passed. | Migration; runtime role separation; `RUN_INTEGRATION=1`; form race; outbox two-worker; webhook guard/delivery; restore; later gate summaries. | User-provided GitHub Actions log; run URL not supplied. Reviewer 1: project owner. Reviewer 2: independent review pending. |
| #3 | `30a3d7f` | **FAIL** | `P1-DB`: `uv run alembic upgrade head` failed at `migrations/env.py:24` while `get_settings()` constructed `Settings()`; required `telegram_bot_token`, `telegram_webhook_secret`, and `public_base_url` were absent. | Lock; quality checks; 73 unit tests; validators; 12 security invariants; smoke checks. | Runtime role separation; integration; synthetic webhook guard; later gate summaries. | User-provided GitHub Actions log; run URL not supplied. Reviewer 1: project owner. Reviewer 2: independent review pending. Synthetic Telegram token is settings-load-only; no Telegram contact is made; real delivery remains `BLOCKED`. |
| #4 | `46435a9` | **FAIL** | `P1-DB`: `alembic upgrade head` reached `migrations/versions/20261008_0001_foundation.py:27`; one `op.execute` contained multiple `CREATE TABLE`/`CREATE INDEX` commands and `asyncpg` rejected the prepared statement with `cannot insert multiple commands into a prepared statement`. | Settings load; PostgreSQL connection; admin role; runtime app-role creation; preceding lock/quality/unit/validator/smoke stages recorded by CI. | Runtime role-separation probe; `RUN_INTEGRATION=1`; synthetic webhook guard; later gate summaries. | User-provided GitHub Actions log; run URL not supplied. Reviewer 1: project owner. Reviewer 2: independent review pending. `P1-WEBHOOK-DELIVERY` remains `BLOCKED`; no real Telegram contact was attempted. |
| #5 | `a20c620` | **PARTIAL** | Result: `PARTIAL — 5 gates BLOCKED/NOT_RUN`; every executable gate completed successfully. | `P1-LOCK=PASS`; `P1-SERVICE-HEALTH=PASS`; `P1-OFFLINE=PASS`; `P1-DB=PASS` (`head=0007`); `P1-ROLE=PASS` (`audit.audit_events` DELETE only); `P1-INTEGRATION=PASS` (env-presence only); `P1-WEBHOOK-GUARD=PASS` (function-level). | `P1-SECURITY=BLOCKED`; `P1-WEBHOOK-DELIVERY=BLOCKED`; `P1-RACE=BLOCKED`; `P1-REDIS-WORKERS=BLOCKED`; `P1-RESTORE=BLOCKED`. | [Run #5](https://github.com/AliRabiee2286/account-security-bot/actions/runs/39013722100); disposable PostgreSQL 16 evidence; CI admin role was superuser, so non-superuser migration evidence remains open. Reviewer 1: project owner. Reviewer 2: independent review pending. |

## PR2-A local rehearsal — not a GitHub CI run

Branch: `stg-001-pr2a-connectivity`, based on `main` at `4974554`.
Implementation commit: `2302a0a` (connectivity tests and gate).
This is local Docker evidence only; no new CI run number, CI URL, or reviewer approval is claimed.
The final `P1-INTEGRATION` evidence still requires the Linux GitHub CI run for this implementation.

| Local check | Result | Counts / scope |
|---|---|---|
| PostgreSQL 16 + Redis 7 | PASS | 2 disposable containers; published only on `127.0.0.1`; random process-environment-only passwords |
| Admin migration | PASS | 7 revisions; target head `0007`; admin superuser, runtime `sentinel_app` non-superuser |
| Independent connectivity group | PASS | 3 passed, 0 failed, 0 skipped: existing env contract plus 2 real round-trip tests |
| Full pytest with integration enabled | PASS | 80 passed, 0 failed, 0 skipped |
| Synthetic data cleanup | PASS | 0 probe rows/keys remain; PostgreSQL rollback verified and Redis key deleted |
| Container cleanup | PASS | 0 rehearsal containers remain; anonymous volumes removed |
| Enabled unavailable-service check | PASS (expected failure) | 1 contract passed, 2 service failures, 0 skipped; failures did not disclose DSNs/passwords |
| Ordinary `uv run pytest -q` | PASS (offline scope) | 77 passed, 3 skipped; integration deliberately disabled, not runtime evidence |
| Ruff check / format, mypy, shell syntax, diff check | PASS | `ruff check .`; `ruff format --check .`; `mypy app`; `bash -n scripts/staging_gate.sh`; `git diff --check` |

`P1-INTEGRATION` implementation scope is now **real PostgreSQL + Redis round-trip**.
The gate uses an independent pytest exit code and JUnit counts, not console-log parsing.
The local run made no Telegram/provider contact and did not change `app/`, migrations, or workflow.
Phase 1 remains `PARTIAL`; this rehearsal does not close the other blocked gates or `SEC-004`.
