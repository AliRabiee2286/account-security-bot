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
| P1-REDIS-WORKERS | claim/lease/reclaim semantics; two concurrent in-process workers; lease ownership NOT enforced — stale-worker overwrite confirmed locally (SEC-004); test-only handler; no production handler | PASS (local + Linux CI; independent reviewer pending) | [PR2-D red reclaim receipt](PR2-D-RED-RECLAIM.md); [PR2-D Linux CI run](https://github.com/AliRabiee2286/account-security-bot/actions/runs/39551172150) | |
| P1-CI | uv sync, ruff, mypy, import-linter, pytest | BLOCKED | | |
| P1-RACE | 20 pairs + lock-wait overlap + replay/expiry; PostgreSQL; no HTTP | PASS (Linux CI; independent reviewer pending) | | |
| P1-WEBHOOK | invalid secret 403, valid secret 200 | BLOCKED | | |
| P1-RESTORE | logical PostgreSQL 16 `pg_dump --format=custom`/`pg_restore`; synthetic data; row count + md5 digest; head `0007`; no forbidden privileges after restore (DELETE/TRUNCATE; audit UPDATE); allowed privileges not compared (TEST-005); dump cleanup | PASS (local + Linux CI; independent reviewer pending) | [PR2-E Linux CI run](https://github.com/AliRabiee2286/account-security-bot/actions/runs/40222607578); PR2-E local receipt below | |
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
| `39551172150` | `9466b0a` | **PARTIAL** | `P1-REDIS-WORKERS-XML tests=3 skipped=0 errors=0 failures=0`; `Result: PARTIAL — 3 gates BLOCKED/NOT_RUN`. | `P1-REDIS-WORKERS=PASS` for the merged PR2-D outbox gate. | `P1-SECURITY`, `P1-WEBHOOK-DELIVERY`, and `P1-RESTORE` remain BLOCKED/NOT_RUN. | [PR2-D Linux CI run](https://github.com/AliRabiee2286/account-security-bot/actions/runs/39551172150); Reviewer 1: project owner. Reviewer 2: independent review pending. |
| `40222607578` | `1262177` | **PARTIAL** | `P1-RESTORE-XML tests=2 skipped=0 errors=0 failures=0`; `P1-RESTORE=PASS`; `Result: PARTIAL — 2 gates BLOCKED/NOT_RUN`. | `P1-RESTORE=PASS`; no forbidden privileges after restore (DELETE/TRUNCATE; audit UPDATE); allowed privileges not compared (TEST-005). | `P1-SECURITY` and `P1-WEBHOOK-DELIVERY` remain BLOCKED/NOT_RUN. | [PR2-E Linux CI run](https://github.com/AliRabiee2286/account-security-bot/actions/runs/40222607578); Reviewer 1: project owner. Reviewer 2: independent review pending. |

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

## PR2-C local verification — 2026-10-20, Asia/Tehran

Branch: `stg-001-pr2c-roles`, based on `main` after PR2-B merge.
Implementation commit: `d12092d` (`test: enforce runtime role privileges`).
These are local Docker results, not a GitHub Actions run or independent reviewer approval.
No push, product changes, migration changes, or workflow changes were made for this package.

| Local check | Result | Counts / scope |
|---|---|---|
| Disposable services and migration | PASS | PostgreSQL 16 + Redis 7; loopback-only ports; random process-environment-only passwords; migration head `0007`; runtime role non-superuser |
| Positive role group | PASS | 2 passed, 0 skipped/errors/failures; catalog `table_count=21`, `schema_count=6`, zero table/schema/attribute/membership/database violations |
| Sensitive-table DELETE checks | PASS | `SELECT` succeeded and four runtime DELETE attempts were rejected with SQLSTATE `42501` |
| Temporary DELETE grant control | PASS (expected test failure) | Granting DELETE on `social.credentials` produced 2 failures and identified only `social.credentials`; grant was revoked |
| Temporary TRUNCATE grant control | PASS (expected test failure) | Granting TRUNCATE on a temporary `core` table produced 1 failure and identified that table; table was dropped |
| Audit trigger control | PASS (expected control result) | Temporary audit TRUNCATE reached trigger SQLSTATE `P0001`; it was not accepted as privilege denial; grant was revoked |
| Restored role group | PASS | 2 passed, 0 skipped/errors/failures; catalog returned to 21 tables with zero violations |
| Complete staging gate | PASS (local executable gates) | Exit 0; `P1-ROLE=PASS`, role XML `tests=2`, connectivity XML `tests=3`, race XML `tests=3`, all with zero skips/errors/failures; overall `PARTIAL` with SECURITY, WEBHOOK-DELIVERY, REDIS-WORKERS and RESTORE blocked |
| Offline checks after PR2-C | PASS | Ruff, format, mypy, import-linter, validators, offline smoke, import smoke; `uv run pytest -q` 77 passed, 8 skipped by integration guard |
| Cleanup | PASS | Disposable PostgreSQL/Redis containers removed with `docker rm -fv`; temporary grants, table, reports and harness removed |

The role evidence is limited to PostgreSQL effective privileges. It does not close the
non-superuser migration-admin gap (`SEC-002`), HTTP authorization/CSRF, encryption, provider
delivery, independent review, or production readiness. The temporary negative controls were
external to the repository and are not part of the commit.

## PR2-C Linux CI receipt — merged

PR2-C was merged into `main` at `57d7a85`. Linux CI passed on implementation commit `554335d`:
[run #39386598021](https://github.com/AliRabiee2286/account-security-bot/actions/runs/39386598021).
The CI receipt is runtime evidence for SEC-003; final closure remains pending independent review.

| Linux CI result | Result | Counts / scope |
|---|---|---|
| `P1-ROLE-PRIVILEGES` | PASS | `P1-ROLE-PRIVILEGES-XML tests=2 skipped=0 errors=0 failures=0`; catalog and sensitive-table role checks passed |
| `P1-ROLE` | PASS | Existing audit DELETE probe and role privilege group both passed |
| Overall staging result | `PARTIAL` | `Result: PARTIAL — 4 gates BLOCKED/NOT_RUN` |

Reviewer 1: project owner. Independent reviewer: pending. The next package is PR2-D; its
scope remains claim/lease/reclaim semantics with a local test-only handler, without production
handler activation, `app/` changes, or migration changes.

## PR2-D local verification — 2026-10-20, Asia/Tehran

Branch: `stg-001-pr2d-outbox`, based on merged PR2-C `57d7a85`. These are local Docker results,
not a GitHub Actions run or independent reviewer approval. No push was performed.

| Local check | Result | Counts / scope |
|---|---|---|
| Red evidence before fix | PASS (expected failure) | `tests=3 skipped=0 errors=0 failures=1`; two-worker and mark-failed passed; reclaim failed with `asyncpg.exceptions.UndefinedFunctionError` (`timestamp with time zone < interval`) at `outbox_runner.py:27-29` |
| Approved product fix | PASS | `f4527e7` changes only `app/entrypoints/workers/outbox_runner.py`: `CAST(:age AS interval)`; no schema or migration change |
| Green outbox group | PASS | `tests=3 skipped=0 errors=0 failures=0`; ten synthetic events, one local handler call each; reclaim and retry timing passed |
| Role UPDATE negative control | PASS (expected test failure) | Temporary `GRANT UPDATE (reason)` identified `audit.audit_events`; `tests=1 skipped=0 errors=0 failures=1`; revoke and restored catalog `tests=1 ... failures=0` |
| Claim negative control | PASS (expected test failure) | External claim copy without the status predicate made the two-worker test fail (`tests=1 skipped=0 errors=0 failures=1`); copy/plugin deleted |
| SEC-004 experiment | CONFIRMED | `stale_worker_marked_new_lease=YES`; reclaim=1, intermediate status `delivering`, attempts=2, final status `delivered`, attempts=2; ownership remains outside gate scope |
| Complete staging gate | PASS (local executable gates) | Exit 0; `P1-ROLE=PASS`, `P1-INTEGRATION=PASS`, `P1-RACE=PASS`, `P1-REDIS-WORKERS-XML tests=3 skipped=0 errors=0 failures=0`, `P1-REDIS-WORKERS=PASS`; `P1-RESTORE=BLOCKED` |
| Offline checks during gate | PASS | `uv run pytest -q`: 77 passed, 11 skipped; Ruff, format, mypy, import-linter, validators, offline smoke and import smoke passed |
| Cleanup | PASS | Every disposable container removed with `docker rm -fv`; admin cleanup was scoped to registered IDs; temporary mutation files and harnesses removed |

The exact red receipt is in `evidence/PR2-D-RED-RECLAIM.md`. The outbox gate scope is
**claim/lease/reclaim semantics; two concurrent in-process workers; lease ownership NOT enforced
— stale-worker overwrite confirmed locally (SEC-004); test-only handler; no production handler**.
`P1-RESTORE` remains BLOCKED, and
Linux CI/independent review for PR2-D are still pending.

## PR2-E local verification — 2026-10-25, Asia/Tehran

Branch: `stg-001-pr2e-restore`, based on merged PR2-D `9466b0a`. Implementation commit:
`e3e03d7` (`test: add PR2-E restore round-trip gate`). These are local Docker results, not a
GitHub Actions run or independent reviewer approval. No push was performed. `app/` and
`migrations/` were not changed.

| Local check | Result | Counts / scope |
|---|---|---|
| Independent restore group | PASS | PostgreSQL 16 disposable container; `tests=2 skipped=0 errors=0 failures=0`; source/target table sets, row counts and md5 digests matched; migration head `0007` matched |
| Restore privilege and trigger checks | PASS | No forbidden privileges after restore (DELETE/TRUNCATE; audit UPDATE); allowed privileges not compared (TEST-005); `trg_audit_no_update` and `trg_audit_no_truncate` were present |
| Corrupt-dump control | PASS | Truncating the in-container custom dump made `pg_restore` return non-zero and the target database was dropped afterward |
| Full local staging gate | PASS | `P1-RESTORE-DIAGNOSTIC=pytest_exit=0 xml_exit=0`; `P1-RESTORE=PASS`; `STAGING_GATE_STATUS=0` |
| Digest negative control | PASS (expected mismatch) | Changing one restored `identity.departments` row kept the count equal and changed the md5 digest |
| Count negative control | PASS (expected mismatch) | Deleting one restored `identity.departments` row changed the row count |
| Privilege negative control | PASS (expected violation) | Temporary `GRANT DELETE` to `sentinel_app_role` was detected and then revoked |
| Audit precondition and cleanup | PASS | Source audit count was `0` before the gate and `1` after the successful run; the synthetic audit row was intentionally not deleted because the audit table is append-only; disposable containers were removed |
| Offline/project checks | PASS / known debt | `ruff check .`, `ruff format --check .`, `uv run python -m pytest -q` (`77 passed, 13 skipped`), `bash -n`, and `git diff --check` passed; `uv run mypy .` remains the recorded repository-wide `TEST-003` failure with 46 errors |

The first full-gate attempt failed before restore because the gate inherited `RUN_INTEGRATION=1`
for its offline `uv run pytest -q` step; an earlier integration test left one audit row in the
same disposable database, violating the restore precondition. The focused fix was to run that
offline step with `RUN_INTEGRATION=0` while keeping each later integration group explicitly
enabled. The rerun passed without changing application code or migrations.

This receipt does not claim encrypted backup, PITR, production backup readiness, or independent
review. The three negative-control harnesses and any dump files were kept outside the repository
and removed after the run. Linux CI receipt: `P1-RESTORE-XML tests=2 skipped=0 errors=0 failures=0`,
`P1-RESTORE=PASS`, `Result: PARTIAL — 2 gates BLOCKED/NOT_RUN`.
