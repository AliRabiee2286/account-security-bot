# PR2-D red evidence — reclaim before fix

Date: 2026-10-20, Asia/Tehran  
Branch: `stg-001-pr2d-outbox`  
Code under test: `2e219ad` (before the approved product fix)  
Environment: disposable PostgreSQL 16 + Redis 7; synthetic data only

The complete outbox integration file was run before changing `app/`:

```text
RED_OUTBOX_XML tests=3 skipped=0 errors=0 failures=1
outbox two-workers: events=10 handler_calls=10
outbox mark-failed: retry_scheduled=true
1 failed, 2 passed
```

The two-worker claim test passed: ten synthetic events received exactly ten local test-handler
calls. The separate mark-failed/backoff check also passed. The reclaim test failed on the
existing production path:

```text
error: asyncpg.exceptions.UndefinedFunctionError
operator does not exist: timestamp with time zone < interval
source: app/entrypoints/workers/outbox_runner.py:27-29
wrapped by: sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError
```

Sanitized SQL shape observed by the driver:

```sql
WHERE status='delivering' AND delivering_at < now() - $1
parameter type: datetime.timedelta
```

No DSN, password, payload, token, or row identifier is recorded. The disposable containers and
temporary reports were removed after the run. This red result is the reason the narrowly scoped
interval cast in `reclaim_stuck()` was approved.
