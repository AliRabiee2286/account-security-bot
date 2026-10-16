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
| P1-REDIS | two-worker outbox + stuck reclaim | BLOCKED | | |
| P1-CI | uv sync, ruff, mypy, import-linter, pytest | BLOCKED | | |
| P1-RACE | concurrent form consume, exactly one winner | BLOCKED | | |
| P1-WEBHOOK | invalid secret 403, valid secret 200 | BLOCKED | | |
| P1-RESTORE | encrypted backup restore and checksum | BLOCKED | | |
| P1-SECURITY | review S-011..S-022 applicable controls | BLOCKED | | |
| P1-OFFLINE | lock, compile, unit, Ruff, mypy, import boundaries, offline smoke | PASS (workspace only) | | |

## Release decision

- [ ] PASS: all rows have evidence and two reviewers
- [ ] BLOCKED: at least one row lacks runtime evidence

No production credentials or real employee data may be used for this run.
| P1-LOCK | reviewed `uv.lock` + frozen install | BLOCKED | | |
