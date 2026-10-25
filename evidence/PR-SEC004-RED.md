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

## Local green witness after the product fix

The product fix fences both completion paths with the claimed `attempts` value. On a fresh
disposable PostgreSQL 16 container:

```text
RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_outbox_two_workers.py -k 'stale_worker_cannot_mark_delivered_after_reclaim or stale_worker_cannot_mark_failed_after_reclaim'
tests=2 skipped=0 errors=0 failures=0

RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_outbox_two_workers.py
tests=5 skipped=0 errors=0 failures=0
```

The first command proved the stale delivered and stale failed cases green; the second proved the
complete outbox group green. A separate external temporary copy of the unfenced dispatch module
was injected into the runner and the two new tests returned `tests=2 skipped=0 errors=0 failures=2`
again. The copy, plugin, temporary reports, and disposable container were deleted afterward.

This is local evidence only; Linux CI for SEC-004 is pending. Fencing protects database state only:
an external effect already performed by an old worker is not undone, so real provider handlers
must be idempotent with a key derived from the message identifier.
