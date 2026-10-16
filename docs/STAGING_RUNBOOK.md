# Staging runbook

## Preconditions

- Disposable host, DNS/TLS, Docker Engine and Compose.
- Python 3.12 and `uv` available on the operator host or inside the build environment.
- PostgreSQL 16 and Redis 7 private network only.
- The checked-in `uv.lock`; production installs must use `uv sync --frozen`.
- `.env` from a secret manager, never committed.
- `secrets/master_key` generated outside the DB host and mounted read-only.
- Test Telegram bot, never production bot or real employee credentials.

## Gate

```bash
cp .env.example .env
# fill staging values and create secrets/master_key
make dev
docker compose run --rm migrate
RUN_INTEGRATION=1 ./scripts/staging_gate.sh
```

The gate requires `DATABASE_URL`, `MIGRATION_DATABASE_URL`, and `REDIS_URL`. Runtime must use
the least-privileged `sentinel_app` role; migrations must use the separate `sentinel_admin`
role. Validate the Compose file before starting services:

```bash
docker compose config
uv lock --check
```

## Required evidence

Record git commit, migration revision, test output, race-test winner count, webhook 401/200
results, encrypted backup checksum, restore duration, restored row counts, and reviewer names.

## Abort conditions

Abort immediately if secrets appear in logs, DB/Redis is public, migration is non-repeatable,
more than one concurrent form consume succeeds, an outbox message is delivered twice without
idempotent handler behavior, or restore cannot be verified.

## Rollback

Disable webhook, stop workers, revoke staging sessions/tokens, preserve audit logs, restore the
last known-good DB snapshot into a disposable DB, and record an incident. Never downgrade a
production audit schema to erase evidence.

## Dependency lock

The source workspace contains `uv.lock`; `uv lock --check`, Docker and CI configuration must
agree on the same lockfile. Before a production image is built, review the resolved versions in
a trusted network-enabled environment and keep Docker/CI on `uv sync --frozen`. A successful
offline lock check is not a substitute for a trusted dependency review.

## Database least-privilege

The app connects with `sentinel_app` via `DATABASE_URL`. Alembic uses the separate privileged
`MIGRATION_DATABASE_URL`; never point runtime at the admin role. Migrations grant only the
`sentinel_app_role` group privileges. For existing volumes, init scripts do not rerun; provision
`sentinel_app` and membership deliberately, then rotate credentials. Redis requires a password
and must remain private.

## Restore drill command contract

`scripts/restore_drill.sh` does not evaluate an arbitrary shell string. Supply a verified
executable and optional newline-delimited arguments:

```bash
export RESTORE_EXECUTABLE=pg_restore
export RESTORE_ARGS="--clean
--if-exists
--dbname=sentinel_restore
backup.dump"
./scripts/restore_drill.sh
```

Each line in `RESTORE_ARGS` is passed as one literal argument. Record the checksum, duration,
restored row counts and reviewer in the evidence template.

## Offline status rule

Offline `pytest`, Ruff, mypy, import smoke and static security checks may be PASS while Phase 1
is still BLOCKED. Only disposable staging evidence changes the phase status.
