# Integration gate

These tests require PostgreSQL 16 and Redis 7. They must run in CI/staging, not be replaced by
syntax checks. `RUN_INTEGRATION=1` enables the real-service fixtures; if a service is unavailable,
the fixture fails rather than skipping. The PR2-A connectivity group is run independently with:

```bash
RUN_INTEGRATION=1 uv run pytest -q -rs \
  tests/integration/test_gate_contract.py tests/integration/test_runtime_connectivity.py
```

The connectivity group proves a synthetic PostgreSQL write/read after migration and an
authenticated Redis SET/GET/delete round-trip. No DSN, password, token, or payload is printed.

- Supply `DATABASE_URL` for the `sentinel_app` runtime role (including the existing
  `postgresql+asyncpg://` format), a separate `MIGRATION_DATABASE_URL`, and `REDIS_URL`.
- Provision the runtime role and run `uv run alembic upgrade head` as admin first. The
  PostgreSQL test uses the migrated `core.outbox`, then rolls back and verifies no probe row
  remains; it does not run migrations or write through the admin role.
- Redis keys are random and expire after 30 seconds; deletion is also attempted in `finally`.
  Connect/query operations are bounded by 5 seconds and cleanup by 3 seconds.
- An enabled run with a missing environment, unavailable service, skipped report, or no test
  call reports cannot succeed. An ordinary offline run without `RUN_INTEGRATION=1` skips
  this group intentionally.
- The staging gate runs this group separately, uses the pytest exit code and structured
  JUnit counts (at least 3 cases; zero skips/errors/failures), and deletes temporary reports.
  Console output is not parsed for gate status; only a redacted diagnostic tail is emitted.
- For local Docker runs, remove exactly the containers created by that run with
  `docker rm -fv <container>`. Remove only volumes created by that same run; do not delete
  older or unrelated workspace volumes.

## PR2-B: one-time-form race, overlap, replay, and expiry

```bash
RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_one_time_form_race.py
```

- `test_one_time_form_consume_race`: 20 fresh forms, random tokens and subject/owner UUIDs,
  `purpose=credential_entry`, `owner_type=social_account`, and future expiry. Each pair holds
  two independent `AsyncSession` connections before an `asyncio.Barrier(2)` releases them.
  Actual `current_user=session_user=sentinel_app`, distinct `pg_backend_pid()` values, and
  both commits are checked. Each pair must return one `ConsumedForm` and one `None`; a fresh
  session then checks that the row exists with committed non-NULL `consumed_at`.
- `test_one_time_form_replay_and_expiry`: a valid-but-wrong `social_oauth` purpose returns
  `None` and leaves `consumed_at` NULL; the correct `credential_entry` purpose still wins.
  Replay returns `None`, and an expired form returns `None` while its `consumed_at` remains NULL.
- `test_one_time_form_deterministic_lock_wait`: transaction A consumes and holds its row lock
  without committing; B uses another runtime connection and begins the same consume. An admin
  connection polls `pg_stat_activity` for the B PID with `usename='sentinel_app'`, the current
  database, a different observer PID, and `wait_event_type='Lock'`. Polling uses an async
  timeout and event-loop yield only—no guessed sleep. A then commits; A is the sole
  `ConsumedForm` winner, B is `None`, both transactions commit, and a fresh read sees
  non-NULL `consumed_at`.
- The file-local fixture requires `postgresql+asyncpg` URLs for `sentinel_app` and
  `sentinel_admin`, and checks actual database roles. Enabled missing configuration or an
  unavailable service fails, never skips. Offline runs deliberately skip these two cases.
- Runtime cannot DELETE. Hashes are registered before issuance commits; cleanup connects
  through `MIGRATION_DATABASE_URL`, deletes **only those hashes**, commits, and checks their
  count is zero. No migration, schema changes, or blanket table cleanup occur in the fixture.
- Connection/query timeouts are 5 seconds, whole operations 15 seconds, session/engine close
  5 seconds, and a concurrent pair 20 seconds. Driver errors are replaced by static failures
  outside exception handlers, SQL parameters are hidden, and raw tokens are excluded from repr.
  Neither tokens nor DSNs belong in assertions, logs, reports, or evidence.

`staging_gate.sh` reuses `run_pytest_group <gate-name> <minimum-tests> <test-files...>` for
independent invocations: connectivity requires at least 3 tests and race at least 3. Both
require pytest exit 0 and valid JUnit with zero skips, errors, and failures. Temporary output
and XML are removed on exit; XML counts, not log text, determine the result.

Race scope: **one-time form consume; 20 barrier-synchronized pairs + 1 lock-wait overlap case,
exactly one winner each; PostgreSQL; no HTTP**. This does not establish
HTTP/CSRF/authorization, encryption, or provider behavior. At the time of the PR2-B run,
`P1-RESTORE` was still BLOCKED.

The local negative control injected an external copy of `consume_form` with only
`consumed_at IS NULL` removed. The barrier race and the lock-wait overlap test both fail with
`winners=2, losers=0`; the independent gate rejects the mutated group. Original-code reruns
pass. All mutation/plugin files are outside the repository, are deleted with the disposable
containers, and no product patch is part of the control.

## PR2-C: runtime role privilege and catalog sweep

```bash
RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_runtime_role_privileges.py
```

- Provision `sentinel_app` and run all migrations as `sentinel_admin` before enabling the group.
  `DATABASE_URL` must use `sentinel_app`; `MIGRATION_DATABASE_URL` must use
  `sentinel_admin`. The test verifies `current_user=session_user` for both connections and
  checks that the admin and runtime connections target the same database.
- The first test performs an allowed `SELECT` and a real `DELETE ... WHERE false` attempt on
  `social.credentials`, `identity.sessions`, `identity.mfa_credentials`, and
  `identity.approval_requests`. Every rejection must be PostgreSQL `SQLSTATE 42501`; a trigger
  rejection is not accepted as a privilege result.
- The second test queries PostgreSQL catalogs with the runtime role name. It requires all six
  application schemas, the four sensitive tables and `audit.audit_events`, then sweeps every
  ordinary or partitioned table in those schemas. The effective runtime role must have no
  `DELETE` or `TRUNCATE` anywhere, no `UPDATE` on audit tables, and no `CREATE` on application
  schemas. It also verifies restricted runtime role attributes and membership in
  `sentinel_app_role`.
- `staging_gate.sh` runs this file independently as `P1-ROLE-PRIVILEGES` with a minimum of two
  cases. `P1-ROLE` is `PASS` only when this JUnit-checked group and the existing audit DELETE
  probe both pass with zero skips, errors, and failures. Output contains counts and sanitized
  table/schema names only; DSNs and passwords are never printed.
- PR2-C changes only the role integration test and gate wiring. A temporary grant of `DELETE`
  or `TRUNCATE` is an expected negative control in disposable PostgreSQL: the relevant test
  must fail, the grant must be revoked, and the restored group must pass. A temporary
  `TRUNCATE` on `audit.audit_events` must produce trigger `SQLSTATE P0001`, which is explicitly
  not accepted as a privilege denial.
- This proves PostgreSQL role separation only. It does not prove a non-superuser migration
  role, HTTP authorization/CSRF, encryption, provider delivery, or production readiness.

## PR2-D: outbox claim, reclaim, and retry timing

```bash
RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_outbox_two_workers.py
```

- The file contains five cases. The two-worker case inserts ten `pr2d.synthetic` events and
  one non-target control row, starts two concurrent `run_once()` calls behind a barrier, and
  uses only a local test handler. Every target row must receive exactly one handler call,
  finish `delivered` with `attempts=1`, and the non-target row must remain unchanged.
- The reclaim case inserts a `delivering` row, uses `sentinel_admin` to move `delivering_at`
  into the past, calls `reclaim_stuck(age=...)` without sleeping, and then delivers the row
  exactly once through `run_once()`. The third case checks the existing `mark_failed()` and
  `backoff()` path: the explicit `CAST(:delay AS interval)` schedules a future retry. The fourth
  and fifth cases pause worker A in a local test-only handler, reclaim the row, let worker B claim
  `attempts=2`, and verify that stale delivered and failed completions from A do not change
  database state; B then completes the row.
- Fixtures require PostgreSQL roles `sentinel_app` and `sentinel_admin` and fail when enabled
  configuration or services are missing. Runtime inserts only synthetic rows; cleanup uses
  only the admin connection and only the IDs registered by the current test. No payload, DSN,
  password, token, or row identifier is printed.
- `staging_gate.sh` runs this file independently as `P1-REDIS-WORKERS` with a minimum of five
  cases. Its exact scope is: **claim/lease/reclaim semantics; two concurrent in-process workers;
  lease ownership enforced by attempts fencing (SEC-004: stale worker cannot mark delivered or
  failed); test-only handler; no production handler; DB state only; handlers must be idempotent**.
  In the PR2-D receipt, `P1-RESTORE` was still BLOCKED.
- Before the fix, the group produced `tests=3 skipped=0 errors=0 failures=1`: the two-worker
  case and mark-failed case passed, while reclaim failed with
  `asyncpg.exceptions.UndefinedFunctionError` because `now() - :age` was untyped. The
  sanitized red receipt is `evidence/PR2-D-RED-RECLAIM.md`; the production fix is limited to
  `app/entrypoints/workers/outbox_runner.py`.
- A temporary external claim copy without the status predicate made the two-worker test fail
  by repeatedly claiming work. The copy and plugin were deleted after the negative control.
  The SEC-004 red receipt is `evidence/PR-SEC004-RED.md`. Before the fix, a stale worker changed
  replacement lease state; after the fix the two new cases and the full five-case group are green
  locally. An external temporary copy of the unfenced dispatch module makes both new cases red
  again and is deleted after the control.

The PR2-D/SEC-004 gate proves PostgreSQL primitive semantics and database-state fencing only. It
does not prove provider delivery, HTTP behavior, or production readiness. Fencing does not undo an
external effect already performed by a stale worker; real provider handlers must be idempotent with
a key derived from the message identifier. Linux CI for SEC-004 is pending.

## PR2-E: logical PostgreSQL restore round trip

```bash
RUN_INTEGRATION=1 uv run pytest -q \
  tests/integration/test_restore_roundtrip.py
```

- Set `RESTORE_POSTGRES_CONTAINER` to the running PostgreSQL 16 container name. The fixture
  requires a `sentinel_admin` `MIGRATION_DATABASE_URL` and fails if the named container is absent;
  it never turns an enabled missing-service run into a skip.
- The module seeds only synthetic rows, including a delivered `core.outbox` row and one
  append-only `audit.audit_events` row. The audit table must be empty before setup; the synthetic
  audit row is intentionally not deleted. Non-audit synthetic rows are deleted with admin during
  cleanup.
- `pg_dump --format=custom` and `pg_restore` run through list-argument `docker exec` calls,
  use `-U sentinel_admin`, keep the dump at a randomized `/tmp` path inside the container, and
  remove it during cleanup. No `--no-owner` or `--no-acl` flags are used. Subprocesses are bounded
  and raw output is not emitted.
- The positive case compares the source and target table sets, every table's row count and md5
  digest, migration head `0007`, no forbidden privileges after restore (DELETE/TRUNCATE; audit
  UPDATE); allowed privileges not compared (TEST-005), and the two audit trigger names.
  The corrupt-dump case requires non-zero `pg_restore` and verifies that its target database is
  dropped.
- `staging_gate.sh` runs this file independently as `P1-RESTORE` with a minimum of two cases.
  Its offline suite explicitly sets `RUN_INTEGRATION=0`; later integration groups opt in with
  `RUN_INTEGRATION=1`. This prevents an earlier integration test from leaving an audit row that
  would invalidate the restore precondition.
- PR2-E is merged into `main` at `1262177`. The local receipt and Linux CI run
  [40222607578](https://github.com/AliRabiee2286/account-security-bot/actions/runs/40222607578)
  both report `tests=2 skipped=0 errors=0 failures=0` and `P1-RESTORE=PASS`; CI overall is
  `Result: PARTIAL — 2 gates BLOCKED/NOT_RUN`. Separate disposable controls detected an md5
  mismatch after a row update, a count mismatch after a row deletion, and a temporary forbidden
  `DELETE` privilege, then restored the database state. The privilege scope is no forbidden
  privileges after restore (DELETE/TRUNCATE; audit UPDATE); allowed privileges not compared
  (TEST-005). Independent review remains pending.

Required later cases: rollback on failed audit write; HTTP webhook valid/invalid; encrypted
credential cannot be read as plaintext; encrypted/PITR production backup evidence. See
`docs/NEXT_SESSION.md` for the remaining PR boundaries.
