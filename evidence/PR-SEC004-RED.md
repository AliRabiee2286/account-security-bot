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
tests=6 skipped=0 errors=0 failures=0
```

The first command proved the stale delivered and stale failed cases green; the second proved the
complete six-case outbox group green. A separate external temporary copy of the unfenced dispatch
module was injected into the runner and the two new tests returned
`tests=2 skipped=0 errors=0 failures=2` again. The copy, plugin, temporary reports, and disposable
container were deleted afterward.

This is local evidence only; Linux CI for SEC-004 is pending. Fencing protects database state only:
an external effect already performed by an old worker is not undone, so real provider handlers
must be idempotent with a key derived from the message identifier.

## Third fence scenario: stale failure after replacement delivered

Test: `test_stale_failure_after_replacement_delivered_keeps_row_delivered`.

The event-coordinated test pauses worker A after its `attempts=1` claim, reclaims the row, lets
worker B claim `attempts=2` and complete successfully, then releases A to raise a synthetic
failure. The final database-state assertion requires `delivered`, `attempts=2`, unchanged
`delivered_at`, and unchanged `last_error`.

```text
Old mark_failed control (temporary external copy; WHERE id = :id only): tests=1 skipped=0 errors=0 failures=1
Fenced product test: tests=1 skipped=0 errors=0 failures=0
```

The old-copy failure was the expected database-state assertion failure: stale failure reverted the
replacement delivered row. No payload, message identifier, DSN, password, or provider data is
recorded here.
