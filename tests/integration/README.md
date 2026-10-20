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
HTTP/CSRF/authorization, encryption, or provider behavior. `P1-REDIS-WORKERS` and
`P1-RESTORE` remain BLOCKED.

The local negative control injected an external copy of `consume_form` with only
`consumed_at IS NULL` removed. The barrier race and the lock-wait overlap test both fail with
`winners=2, losers=0`; the independent gate rejects the mutated group. Original-code reruns
pass. All mutation/plugin files are outside the repository, are deleted with the disposable
containers, and no product patch is part of the control.

Required later cases: rollback on failed audit write; outbox two-worker claim has one winner;
stuck delivery reclaim; HTTP webhook valid/invalid; encrypted credential cannot be read as
plaintext; restore drill. See `docs/NEXT_SESSION.md` for the remaining PR boundaries.
