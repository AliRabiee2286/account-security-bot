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
| P1-RACE | 20 pairs + lock-wait overlap + replay/expiry; PostgreSQL; no HTTP | PASS (Linux CI; independent reviewer pending) | | |
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
At the time of that rehearsal, Linux CI evidence was pending. PR2-A has since merged as
`3700466` ([PR #3](https://github.com/AliRabiee2286/account-security-bot/pull/3)); this session
confirmed the merge with `git pull --ff-only origin main`, but collected no additional CI receipt.

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

## PR2-B local verification — 2026-10-19, Asia/Tehran

Branch: `stg-001-pr2b-race`, created after `git pull --ff-only origin main` at `3700466`.
Implementation commit: `9a4914c` (`test: verify one-time form lock overlap`).
These are local Docker results, not a GitHub Actions run or independent reviewer approval.
No push, product changes, migration changes, or workflow changes were made for this package.

PR2-B was subsequently merged into `main` as `59a9da2`. Linux CI passed for implementation
commit `63a94e7`: [run #39372008697](https://github.com/AliRabiee2286/account-security-bot/actions/runs/39372008697).
Reviewer 1: project owner. Independent reviewer: pending.

| Linux CI result | Result | Counts / scope |
|---|---|---|
| PR2-B race group | PASS | `P1-RACE-XML tests=3 skipped=0 errors=0 failures=0`; `P1-RACE=PASS` |
| Overall staging result | `PARTIAL` | `Result: PARTIAL — 4 gates BLOCKED/NOT_RUN` |

| Local check | Result | Counts / scope |
|---|---|---|
| Disposable services and migration | PASS | PostgreSQL 16 + Redis 7; authenticated TCP; loopback-only ports; random in-memory/process-environment passwords; head `0007`; admin superuser, runtime non-superuser |
| Connectivity, independent pytest | PASS | `tests=3 skipped=0 errors=0 failures=0`, exit 0; original files and `P1-INTEGRATION` scope unchanged |
| Race/overlap/replay/expiry, independent pytest | PASS | `tests=3 skipped=0 errors=0 failures=0`, exit 0 |
| Concurrent pairs | PASS | 20 fresh forms; 20 winners + 20 losers; exactly one each per pair; distinct backend PIDs and actual runtime role; 40 consumer commits; 20 non-NULL post-commit reads |
| Lock-wait overlap | PASS | A held the row lock; admin observed B with `usename=sentinel_app`, current datname, distinct observer PID and `wait_event_type=Lock`; A committed the sole winner, B returned empty and committed |
| Purpose, replay and expiry | PASS | Wrong valid purpose `social_oauth` left `consumed_at` NULL; correct `credential_entry` won; replay and expired form rejected; expired row remains unconsumed |
| Scoped admin cleanup | PASS | Runtime DELETE privilege is false; fixture deletes only registered hashes, commits and reads back zero; an unrelated synthetic sentinel row survived successful and failed runs |
| Actual-test negative control | PASS (expected test failure) | External `consume_form` copy without `consumed_at IS NULL`: barrier and lock-wait tests fail with `winners=2, losers=0`; the lock-wait run was `tests=1 skipped=0 errors=0 failures=1` |
| Original-code rerun after negative control | PASS | 3 passed, zero skips/errors/failures; 20 pairs and the overlap case again produced one winner each |
| Full enabled pytest | PASS | 83 passed; zero skips/errors/failures |
| Enabled missing-env / unavailable-service probes | PASS (expected setup errors) | Each invocation: `tests=2 skipped=0 errors=2 failures=0`, nonzero exit; no DSN/password emitted |
| Complete staging gate | PASS (local executable gates) | Exit 0; integration XML `tests=3`, race XML `tests=3`, all zero skip/error/failure; summary `PARTIAL`, 4 BLOCKED/NOT_RUN gates: SECURITY, WEBHOOK-DELIVERY, REDIS-WORKERS, RESTORE |
| Staging gate under negative-control injection | PASS (expected gate failure) | Connectivity still exit 0 and 3 clean cases; lock-wait negative XML `tests=1 skipped=0 errors=0 failures=1`, assertion `winners=2, losers=0`; summary would be `FAIL`, `P1-RACE=FAIL` |
| JUnit and runner boundaries | PASS | 16 validator scenarios, including valid reports, minimum counts, skip/error/failure, malformed/empty/nested/inconsistent reports; invalid helper inputs and `mktemp` failure rejected even inside `if` |
| Ordinary `uv run pytest -q` | PASS (offline scope) | 77 passed, 6 skipped deliberately with integration disabled; not runtime evidence |
| `uv run ruff check .` | PASS | No violations |
| `uv run ruff format --check .` | PASS | 167 files already formatted |
| `uv run mypy app` | PASS | 100 source files, no issues |
| `bash -n scripts/staging_gate.sh`; `git diff --check` | PASS | Shell syntax and whitespace clean |
| Final cleanup | PASS | Synthetic forms zero after scoped sentinel removal; no verification containers remain; anonymous volumes removed; external mutation/plugin/harness files and temporary reports deleted |

Successful group diagnostics:

```text
P1-INTEGRATION-DIAGNOSTIC=pytest_exit=0 xml_exit=0
P1-INTEGRATION-XML tests=3 skipped=0 errors=0 failures=0
P1-RACE-DIAGNOSTIC=pytest_exit=0 xml_exit=0
P1-RACE-XML tests=3 skipped=0 errors=0 failures=0
one-time-form race: pairs=20 winners=20 losers=20 consumed_after_commit=20
```

Reproduction commands, after disposable role provisioning and admin migration:

```bash
RUN_INTEGRATION=1 uv run pytest -q \
  tests/integration/test_gate_contract.py tests/integration/test_runtime_connectivity.py
RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_one_time_form_race.py
RUN_INTEGRATION=1 uv run pytest -q
bash scripts/staging_gate.sh
```

On Windows, the local full gate used Git Bash explicitly and a disposable `psql` wrapper
calling the PostgreSQL 16 container's TCP client. An initial Python subprocess selected WSL's
`bash` and could not start it; correcting the external runner path required no repository fix.
The negative control injected only the external consume copy, not a modified `app/` file.
Its two-winner result is intentional; the original primitive never produced multiple winners
in these runs. If it does, stop and report `app/core/one_time_form_store.py:61-78` instead of
patching product code or schema in PR2-B.

`P1-RACE` scope: **one-time form consume; 20 barrier-synchronized pairs + 1 lock-wait overlap
case, exactly one winner each; PostgreSQL; no HTTP**. This is not HTTP/CSRF/authorization/encryption evidence. Independent review
remains pending; Phase 1 is still `PARTIAL` and Phase 2
is still `BLOCKED`. `P1-REDIS-WORKERS`, `P1-RESTORE`, and `SEC-004` are not closed.
