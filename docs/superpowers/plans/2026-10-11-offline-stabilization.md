# Offline Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use task-by-task execution with an independent verification checkpoint after each task. Do not claim a task complete without running its listed command.

**Goal:** Make the Sentinel foundation importable, type-safe, lint-clean, reproducible, and ready for truthful staging verification without enabling real external providers.

**Architecture:** Keep the modular monolith and public `api.py` contracts. Move shared token hashing into `core`, invert the core-to-audit dependency through a callback Protocol, keep RBAC least-privilege inheritance, and make CI/Docker/Alembic use the same locked configuration model.

**Tech Stack:** Python 3.12, uv, FastAPI, aiogram 3, SQLAlchemy 2 async, Alembic, PostgreSQL 16, Redis 7, arq, Ruff, mypy strict, pytest, import-linter.

## Global Constraints

- No real credentials, Telegram tokens, employee data, provider accounts, or external deletion operations.
- Do not mark Phase 1 or Phase 2 complete; runtime evidence remains authoritative.
- Preserve append-only audit, redaction, request IDs, one-time atomic consume, envelope encryption, and fail-closed authentication.
- Role hierarchy follows least privilege: senior roles inherit descendant permissions; junior roles do not inherit parent permissions.
- Entry points import module public APIs only; modules own their repositories/models.
- Run the smallest relevant test after every task, then run the full offline gate before the next task.

---

### Task 1: Establish locked reproducibility and config gate

**Files:**
- Modify: `scripts/validate_config.py`
- Modify: `Dockerfile`
- Modify: `scripts/staging_gate.sh`
- Modify: `.env.example`
- Test: `tests/unit/test_release_config.py`

**Interfaces:**
- Produces a config validator that requires `uv.lock` and frozen-install markers.
- Keeps runtime `DATABASE_URL` separate from migration `MIGRATION_DATABASE_URL`.

- [x] **Step 1: Write failing tests for the new lock contract**

Add tests that assert the validator accepts an existing `uv.lock`, requires `MIGRATION_DATABASE_URL`, and rejects a config template that removes the runtime/migration split.

- [x] **Step 2: Run the focused tests**

Run: `uv run pytest -q tests/unit/test_release_config.py`

Expected: the new tests fail because the validator still asserts that `uv.lock` must not exist.

- [x] **Step 3: Update the validator and staging gate**

Replace the negative lock assertion with an existence check and a clear failure message. Add `MIGRATION_DATABASE_URL` and `REDIS_URL` required checks to `scripts/staging_gate.sh`. Keep `uv sync --frozen` as the first dependency action.

- [x] **Step 4: Make the production image frozen**

Copy `uv.lock` in `Dockerfile` before install and replace the non-frozen install with `uv sync --frozen --no-dev`.

- [x] **Step 5: Run the focused checks**

Run: `uv lock --check; python scripts/validate_config.py; uv run pytest -q tests/unit/test_release_config.py`

Expected: all commands exit 0.

### Task 2: Repair Compose and CI runtime configuration

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.github/workflows/ci.yml`
- Modify: `docker/postgres/init/01-runtime-role.sh`
- Modify: `pyproject.toml` (add direct dev dependency `pyyaml>=6.0` for deployment parsing tests)
- Test: `tests/unit/test_deployment_config.py`

**Interfaces:**
- Compose exposes no database or Redis port publicly by default.
- CI migration uses `MIGRATION_DATABASE_URL`; application checks use `DATABASE_URL`.

- [x] **Step 1: Add deployment parsing tests**

Create a test that loads `docker-compose.yml` with PyYAML, asserts the Redis command is a valid list, checks the Redis password flag, and confirms API/worker services depend on healthy DB and Redis.

- [x] **Step 2: Run the test to reproduce the current failure**

Run: `uv run pytest -q tests/unit/test_deployment_config.py`

Expected: the YAML load fails at the Redis command quoting.

- [x] **Step 3: Fix Compose quoting and keep private networking**

Represent the Redis command as a YAML-safe block/list so the shell receives `$$REDIS_PASSWORD` without nested unescaped quotes. Do not add host ports for DB or Redis.

- [x] **Step 4: Align CI service roles**

Use a PostgreSQL service with `sentinel_admin`, create the non-privileged `sentinel_app` login in a test setup step, set both database URLs explicitly, and add a Redis service with a non-production test password. Keep test credentials scoped to CI only.

- [x] **Step 5: Run deployment checks**

Run: `uv run pytest -q tests/unit/test_deployment_config.py; uv run python -c "import yaml; yaml.safe_load(open('docker-compose.yml', encoding='utf-8')); print('compose ok')"`

Expected: both commands pass.

### Task 3: Make Alembic and application imports reproducible

**Files:**
- Modify: `alembic.ini`
- Modify: `migrations/env.py` only if configuration alone is insufficient
- Create: `app/core/token_hash.py`
- Modify: `app/core/session.py`
- Modify: `app/core/one_time_form.py`
- Modify: `app/core/one_time_form_store.py`
- Modify: `app/core/auth_resolver.py`
- Test: `tests/unit/test_token_hash.py`
- Test: `tests/unit/test_import_smoke.py`

**Interfaces:**

```python
def hash_token(raw_token: str) -> str: ...
def matches_token(raw_token: str, stored_hash: str) -> bool: ...
```

- [x] **Step 1: Add failing token-hash tests**

Test deterministic SHA-256 output, constant-time matching for a correct token, and rejection of a wrong token. Assert the raw token is not part of the stored digest.

- [x] **Step 2: Run focused tests and import smoke**

Run: `uv run pytest -q tests/unit/test_token_hash.py tests/unit/test_import_smoke.py`

Expected: token tests fail until the module exists; import smoke reports the current `hash_token` import failure.

- [x] **Step 3: Implement the shared primitive and update callers**

Move the hash implementation to `app/core/token_hash.py`, make session verification use it, and import it from one-time forms and the auth resolver. Do not persist or log raw values.

- [x] **Step 4: Make import smoke deterministic**

Create `scripts/import_smoke.py` that discovers `app.*` modules with `pkgutil`, imports each under safe dummy environment variables, collects every failure, and exits non-zero with module names and exception types if any import fails.

- [x] **Step 5: Fix the Alembic package path**

Add the standard project-root path setting to `alembic.ini`. Keep `migrations/env.py` using `migration_database_url` first and `database_url` only as an explicit fallback.

- [x] **Step 6: Verify the task**

Run: `uv run pytest -q tests/unit/test_token_hash.py tests/unit/test_import_smoke.py; uv run python scripts/import_smoke.py; uv run alembic upgrade head`

Expected: tests and import smoke pass. Alembic must no longer fail with `ModuleNotFoundError: app`; without a database it may fail only at the database connection stage.

### Task 4: Restore the module boundary without losing audit events

**Files:**
- Modify: `app/core/session_service.py`
- Modify: `app/core/audit_contract.py` or replace it with a Protocol-only module
- Modify: `app/modules/audit/api.py`
- Modify: `pyproject.toml`
- Modify: `scripts/check_module_boundaries.py`
- Test: `tests/unit/test_audit_contract.py`

**Interfaces:**

```python
class SecurityAuditRecorder(Protocol):
    async def __call__(
        self, session: AsyncSession, *, action: str, actor_id: UUID, target_id: UUID
    ) -> None: ...
```

- [x] **Step 1: Add a failing boundary test**

Test that importing `app.core.session_service` does not import `app.modules.audit`, and test a fake recorder receives the revoke event.

- [x] **Step 2: Run the focused tests and import-linter**

Run: `uv run pytest -q tests/unit/test_audit_contract.py; uv run lint-imports`

Expected: the fake-recorder test cannot yet call the current signature, and the layer contract reports `app.core.audit_contract -> app.modules.audit`.

- [x] **Step 3: Invert the dependency**

Make core define only the Protocol and require the recorder in `revoke_session`. Add an adapter function in the audit public API with the exact Protocol signature. No core file may import `app.modules.*`.

- [x] **Step 4: Adjust import-linter for public APIs**

Allow indirect imports through a module `api.py` facade while keeping direct entrypoint imports of repositories/models forbidden. Extend the AST checker to scan `app/entrypoints` for direct internal imports.

- [x] **Step 5: Verify the boundary**

Run: `uv run pytest -q tests/unit/test_audit_contract.py; uv run lint-imports; python scripts/check_module_boundaries.py`

Expected: all pass and no `app.core -> app.modules` dependency remains.

### Task 5: Enforce least-privilege RBAC and update tests

**Files:**
- Modify: `app/modules/identity/rbac.py` only if needed for explicit semantics
- Modify: `app/modules/identity/permissions.py` if observer visibility metadata is needed
- Modify: `tests/unit/test_rbac.py`
- Modify: `app/modules/identity/README.md`
- Create: `docs/adr/ADR-006-rbac-least-privilege.md`

**Interfaces:**
- `RoleGraph.effective_permissions` keeps senior-inherits-descendant behavior.
- `authorize(..., operation="view" | "execute")` distinguishes read-only visibility from action execution.
- `PermissionDef.observer_may_view` is true only for read permissions (`employee.self.view`, `employee.view`, `audit.view`); it never bypasses `observer_may_execute`.

- [x] **Step 1: Rewrite the failing RBAC assertions**

Assert that `support` retains `employee.approve`, does not receive `audit.view` unless explicitly assigned, and cannot execute `incident.content.remove` without the required second approval. Keep the observer destructive-action denial test.

- [x] **Step 2: Run the focused RBAC tests**

Run: `uv run pytest -q tests/unit/test_rbac.py`

Expected: the old test passes only after its contradictory expectation is replaced with the approved least-privilege contract.

- [x] **Step 3: Implement only the minimum policy correction**

Do not reverse inheritance to parent-to-child. Add `observer_may_view: bool = False` to `PermissionDef`, set it only on the three read permissions in `CATALOGUE`, and add an `operation: Literal["view", "execute"] = "execute"` argument to `authorize`. A super observer may use an absent permission only for `operation="view"`; an execute request must still pass normal membership, scope, observer, and dual-approval checks. The repository must derive the same read-only flag from the permission code so no database migration is needed for this policy.

- [x] **Step 4: Document the accepted rule**

Add ADR-006 with the role tree, inheritance direction, the exact `operation` distinction, observer visibility list, self-action denial, dual approval, and two concrete examples of allowed and denied actions.

- [x] **Step 5: Verify RBAC and security invariants**

Run: `uv run pytest -q tests/unit/test_rbac.py tests/unit/test_security_primitives.py; python scripts/security_invariants.py`

Expected: all pass.

### Task 6: Clear strict typing and adapter contracts

**Files:**
- Modify: `app/modules/identity/webauthn_contract.py`
- Modify: `app/adapters/social/base.py`
- Modify: `app/adapters/social/official_stubs.py`
- Modify: `app/entrypoints/workers/arq_jobs.py`
- Modify: `app/entrypoints/workers/outbox_runner.py`
- Modify: `app/modules/identity/service.py`
- Modify: `app/modules/identity/approval.py`
- Modify: `app/modules/mailboxes/service.py`
- Modify: `app/entrypoints/api/auth.py`
- Modify: `app/entrypoints/api/approval.py`
- Modify: `app/entrypoints/api/incidents.py`
- Test: existing unit tests plus targeted type-check

**Interfaces:**
- Protocols use `Mapping[str, object]` or a typed response model rather than bare `dict`.
- Empty worker handler registries are explicitly typed as `dict[str, Handler]`.
- Stub adapters keep explicit safe `NotImplementedError` behavior and complete annotations.

- [x] **Step 1: Add or update tests for typed boundaries**

Keep the WebAuthn fail-closed test, adapter stub capability tests, and worker empty-registry test. The tests must verify behavior, not merely annotations.

- [x] **Step 2: Run mypy to capture the current failure set**

Run: `uv run mypy app`

Expected: the known 25-error baseline is visible before edits.

- [x] **Step 3: Fix annotations without weakening strict mode**

Add concrete generic types, return annotations, `cast` only at SQLAlchemy result boundaries, and explicit `NoReturn`/typed returns for stubs where appropriate. Remove unused `type: ignore` comments.

- [x] **Step 4: Verify typing and related tests**

Run: `uv run mypy app; uv run pytest -q tests/unit`

Expected: mypy exits 0 and unit tests have zero failures.

### Task 7: Normalize formatting and harden static scripts

**Files:**
- Modify: all project files reported by Ruff, limited to `app/`, `migrations/`, `scripts/`, and `tests/`
- Modify: `scripts/restore_drill.sh`
- Test: full Ruff and script suite

**Interfaces:**
- Static scripts exit non-zero with explicit exceptions rather than relying on Python `assert` statements that disappear under optimization.
- Restore drill does not execute an arbitrary shell string via `eval`.

- [x] **Step 1: Run Ruff in report-only mode**

Run: `uv run ruff check .; uv run ruff format --check .`

Expected: baseline errors are recorded; no files are changed by this step.

- [x] **Step 2: Replace unsafe static assertions**

Update validators and smoke scripts to use explicit `if condition: raise SystemExit(...)` checks. Preserve their messages and exit semantics.

- [x] **Step 3: Replace restore `eval` with an approved command interface**

Accept a verified executable plus arguments through a documented array-style environment contract or require an operator-supplied wrapper path. Reject an empty value and do not interpolate arbitrary text into a shell command.

- [x] **Step 4: Apply Ruff’s safe fixes and format**

Run: `uv run ruff check . --fix; uv run ruff format .`

Review the resulting diff for migration SQL, security checks, and test semantics; do not accept unsafe fixes automatically.

- [x] **Step 5: Verify static quality**

Run: `uv run ruff check .; uv run ruff format --check .; python -m compileall -q app tests migrations scripts`

Expected: all pass.

### Task 8: Run the complete offline gate and update project memory

**Files:**
- Modify: `README.md`
- Modify: `docs/STAGING_RUNBOOK.md`
- Modify: `evidence/PHASE1_EVIDENCE_TEMPLATE.md`
- Modify: attached/project Second Brain copy in the workspace
- Modify: `findings.md`, `progress.md`, `task_plan.md`

**Interfaces:**
- Documentation distinguishes `PASS`, `BLOCKED`, and `NOT RUN`.
- Phase 1 remains blocked when runtime evidence is absent.

- [x] **Step 1: Run the complete offline gate**

Run:

```bash
uv lock --check
python -m compileall -q app tests migrations scripts
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run lint-imports
python scripts/validate_migrations.py
python scripts/validate_config.py
python scripts/check_model_annotations.py
python scripts/validate_migration_semantics.py
python scripts/check_module_boundaries.py
python scripts/check_db_role_separation.py
python scripts/security_invariants.py
python scripts/offline_smoke.py
python scripts/import_smoke.py
```

- [x] **Step 2: Record exact results**

Write command outcomes and counts to `progress.md` and `findings.md`. If a command fails, keep the task open and fix the failure before reporting the package complete.

- [x] **Step 3: Update user-facing setup instructions**

Update README and runbook for the locked install, separate migration URL, Compose validation, and the exact distinction between offline success and staging blockers.

- [x] **Step 4: Update Second Brain**

Append a new session section containing changed files, actual command results, confirmed decisions, remaining blockers, and the single next step: staging runtime or the next approved identity/WebAuthn subproject.

- [x] **Step 5: Final review**

Run: `git status --short` if a repository is later available; otherwise list workspace changes directly and verify no secret files or credentials were added. Re-read the updated Second Brain and report only evidence-backed status.
