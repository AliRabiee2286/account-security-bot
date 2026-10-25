# SEC-004 red receipt

Date: 2026-10-25 (Asia/Tehran)

Scope: two new outbox fencing integration tests on a disposable PostgreSQL 16 container, before
the product fix. The local test handler was defined inside each test; coordination used events and
no guessed sleep. Cleanup used the admin connection for only the test-registered rows, followed by
`docker rm -fv` for the disposable container.

Command:

```text
RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_outbox_two_workers.py -k 'stale_worker_cannot_mark_delivered_after_reclaim or stale_worker_cannot_mark_failed_after_reclaim'
```

Result: `tests=2 skipped=0 errors=0 failures=2`, exit `1`.

| Test | Assertion type | Sanitized result |
|---|---|---|
| `test_stale_worker_cannot_mark_delivered_after_reclaim` | Database-state assertion after stale success | **FAIL** — stale completion changed the replacement lease state. |
| `test_stale_worker_cannot_mark_failed_after_reclaim` | Database-state equality assertion for status/attempts/available_at/last_error | **FAIL** — stale failure changed the replacement failure state. |

No payload, message identifier, DSN, password, or provider data is recorded here.
