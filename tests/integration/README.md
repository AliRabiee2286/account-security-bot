# Integration gate

These tests require PostgreSQL 16 and Redis 7. They must run in CI/staging, not be replaced by
syntax checks. Required cases: all migrations from empty DB; rollback on failed audit write;
one-time form concurrent consume has one winner; outbox two-worker claim has one winner;
stuck delivery reclaim; webhook valid/invalid; encrypted credential cannot be read as plaintext;
restore drill and audit append-only trigger.
