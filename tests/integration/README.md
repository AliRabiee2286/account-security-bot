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
  Console output is not parsed for gate status and raw failure logs are not emitted.

Required later cases: all migrations from empty DB; rollback on failed audit write; one-time form
concurrent consume has one winner; outbox two-worker claim has one winner; stuck delivery reclaim;
webhook valid/invalid; encrypted credential cannot be read as plaintext; restore drill and audit
append-only trigger.
