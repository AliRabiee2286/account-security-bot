#!/usr/bin/env bash
set -euo pipefail
# Run only in a disposable/staging environment with env configured.
EXPECTED_MIGRATION_HEAD=0007
: "${DATABASE_URL:?DATABASE_URL is required}"
: "${MIGRATION_DATABASE_URL:?MIGRATION_DATABASE_URL is required}"
: "${REDIS_URL:?REDIS_URL is required}"
: "${SENTINEL_APP_PASSWORD:?SENTINEL_APP_PASSWORD is required for the disposable runtime role}"
: "${PSQL_ADMIN_DSN:?PSQL_ADMIN_DSN is required for runtime role probes}"
: "${PSQL_RUNTIME_DSN:?PSQL_RUNTIME_DSN is required for runtime role probes}"

P1_LOCK_STATUS=NOT_RUN
P1_SERVICE_HEALTH_STATUS=NOT_RUN
P1_OFFLINE_STATUS=NOT_RUN
P1_SECURITY_STATUS=BLOCKED
P1_DB_STATUS=NOT_RUN
P1_ROLE_STATUS=NOT_RUN
P1_INTEGRATION_STATUS=NOT_RUN
P1_WEBHOOK_GUARD_STATUS=NOT_RUN
P1_WEBHOOK_DELIVERY_STATUS=BLOCKED
P1_RACE_STATUS=BLOCKED
P1_REDIS_WORKERS_STATUS=BLOCKED
P1_RESTORE_STATUS=BLOCKED

redact_file() {
  sed -E \
    -e 's#([Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Tt][Oo][Kk][Ee][Nn]|[Ss][Ee][Cc][Rr][Ee][Tt])=[^[:space:]]+#\1=<redacted>#g' \
    "$1"
}

write_summary() {
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    blocked_count=0
    fail_count=0
    for status in \
      "$P1_LOCK_STATUS" \
      "$P1_SERVICE_HEALTH_STATUS" \
      "$P1_OFFLINE_STATUS" \
      "$P1_SECURITY_STATUS" \
      "$P1_DB_STATUS" \
      "$P1_ROLE_STATUS" \
      "$P1_INTEGRATION_STATUS" \
      "$P1_WEBHOOK_GUARD_STATUS" \
      "$P1_WEBHOOK_DELIVERY_STATUS" \
      "$P1_RACE_STATUS" \
      "$P1_REDIS_WORKERS_STATUS" \
      "$P1_RESTORE_STATUS"; do
      case "$status" in
        BLOCKED|NOT_RUN) blocked_count=$((blocked_count + 1)) ;;
        FAIL) fail_count=$((fail_count + 1)) ;;
      esac
    done
    result=PASS
    if [[ "$blocked_count" -gt 0 ]]; then
      result=PARTIAL
    fi
    if [[ "$fail_count" -gt 0 ]]; then
      result=FAIL
    fi
    {
      printf '%s\n\n' '## PR1 staging gate'
      printf 'Result: %s — %s gates BLOCKED/NOT_RUN\n\n' "$result" "$blocked_count"
      printf '%s\n' '| Gate | Result | Scope |'
      printf '%s\n' '|---|---|---|'
      printf '| P1-LOCK | %s | locked dependency check |\n' "$P1_LOCK_STATUS"
      printf '| P1-SERVICE-HEALTH | %s | PostgreSQL and Redis TCP health |\n' "$P1_SERVICE_HEALTH_STATUS"
      printf '| P1-OFFLINE | %s | static/offline quality checks |\n' "$P1_OFFLINE_STATUS"
      printf '| P1-SECURITY | %s | independent two-reviewer runtime review |\n' "$P1_SECURITY_STATUS"
      printf '| P1-DB | %s | empty database migration and head check |\n' "$P1_DB_STATUS"
      printf '| P1-ROLE | %s | audit.audit_events DELETE only |\n' "$P1_ROLE_STATUS"
      printf '| P1-INTEGRATION | %s | env-presence contract only; no DB/Redis connection |\n' "$P1_INTEGRATION_STATUS"
      printf '| P1-WEBHOOK-GUARD | %s | function-level, no HTTP |\n' "$P1_WEBHOOK_GUARD_STATUS"
      printf '| P1-WEBHOOK-DELIVERY | %s | real Telegram delivery; synthetic token only loads Settings; no Telegram contact; outside PR1 |\n' "$P1_WEBHOOK_DELIVERY_STATUS"
      printf '| P1-RACE | %s | concurrent form consume; test absent in PR1 |\n' "$P1_RACE_STATUS"
      printf '| P1-REDIS-WORKERS | %s | two-worker outbox/reclaim; test absent in PR1 |\n' "$P1_REDIS_WORKERS_STATUS"
      printf '| P1-RESTORE | %s | backup/restore; test absent in PR1 |\n' "$P1_RESTORE_STATUS"
    } >> "$GITHUB_STEP_SUMMARY"
  fi
}

trap write_summary EXIT

if [[ "${CI_SERVICES_HEALTHY:-0}" == "1" ]]; then
  P1_SERVICE_HEALTH_STATUS=PASS
  echo 'P1-SERVICE-HEALTH=PASS PostgreSQL TCP SELECT 1 and Redis TCP PONG verified by CI wrapper'
else
  P1_SERVICE_HEALTH_STATUS=BLOCKED
  echo 'P1-SERVICE-HEALTH=BLOCKED CI wrapper did not provide TCP health evidence' >&2
  exit 1
fi

echo '== offline quality =='
if uv lock --check; then
  P1_LOCK_STATUS=PASS
  echo 'P1-LOCK=PASS'
else
  P1_LOCK_STATUS=FAIL
  echo 'P1-LOCK=FAIL uv lock --check failed' >&2
  exit 1
fi
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run lint-imports
uv run pytest -q
uv run python scripts/validate_migrations.py
uv run python scripts/validate_config.py
uv run python scripts/check_model_annotations.py
uv run python scripts/validate_migration_semantics.py
uv run python scripts/check_module_boundaries.py
uv run python scripts/check_db_role_separation.py
uv run python scripts/security_invariants.py
echo 'P1-SECURITY-STATIC=PASS static security invariant and role-boundary checks'
echo 'P1-SECURITY=BLOCKED independent two-reviewer runtime security review is outside PR1'
uv run python scripts/offline_smoke.py
uv run python scripts/import_smoke.py
P1_OFFLINE_STATUS=PASS
echo 'P1-OFFLINE=PASS'

echo '== runtime role setup =='
role_setup_output="$(mktemp)"
if psql "$PSQL_ADMIN_DSN" \
  --set=ON_ERROR_STOP=1 \
  --set=app_password="$SENTINEL_APP_PASSWORD" >"$role_setup_output" 2>&1 <<'SQL'
SELECT format(
  'CREATE ROLE sentinel_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L',
  :'app_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sentinel_app') \gexec
SQL
then
  rm -f "$role_setup_output"
else
  echo 'P1-ROLE=FAIL runtime role setup failed:' >&2
  redact_file "$role_setup_output" >&2
  rm -f "$role_setup_output"
  P1_ROLE_STATUS=FAIL
  exit 1
fi

echo '== empty database migration =='
migration_output="$(mktemp)"
if uv run alembic upgrade head >"$migration_output" 2>&1; then
  rm -f "$migration_output"
else
  echo 'P1-DB=FAIL migration failed:' >&2
  redact_file "$migration_output" >&2
  rm -f "$migration_output"
  P1_DB_STATUS=FAIL
  exit 1
fi
current_output="$(mktemp)"
heads_output="$(mktemp)"
if uv run alembic current >"$current_output" 2>&1 && uv run alembic heads >"$heads_output" 2>&1; then
  current_revision="$(awk '/\(head\)/ {print $1; exit}' "$current_output")"
  head_revision="$(awk '/\(head\)/ {print $1; exit}' "$heads_output")"
  rm -f "$current_output" "$heads_output"
else
  echo 'P1-DB=FAIL unable to read Alembic current/heads:' >&2
  redact_file "$current_output" >&2
  redact_file "$heads_output" >&2
  rm -f "$current_output" "$heads_output"
  P1_DB_STATUS=FAIL
  exit 1
fi
if [[ "$current_revision" != "$head_revision" || "$head_revision" != "$EXPECTED_MIGRATION_HEAD" ]]; then
  echo "P1-DB=FAIL current=$current_revision heads=$head_revision expected=$EXPECTED_MIGRATION_HEAD" >&2
  P1_DB_STATUS=FAIL
  exit 1
fi
P1_DB_STATUS=PASS
echo "P1-DB=PASS current=heads=$EXPECTED_MIGRATION_HEAD"

echo '== runtime role separation =='
table_output="$(mktemp)"
if psql "$PSQL_ADMIN_DSN" --no-psqlrc --set=ON_ERROR_STOP=1 --tuples-only --no-align \
  --command "SELECT to_regclass('audit.audit_events')" >"$table_output" 2>&1; then
  audit_table="$(tr -d '[:space:]' < "$table_output")"
  rm -f "$table_output"
else
  echo 'P1-ROLE=FAIL admin audit table existence probe failed:' >&2
  redact_file "$table_output" >&2
  rm -f "$table_output"
  P1_ROLE_STATUS=FAIL
  exit 1
fi
if [[ "$audit_table" != 'audit.audit_events' ]]; then
  echo "P1-ROLE=FAIL admin probe did not find audit.audit_events (result=$audit_table)" >&2
  P1_ROLE_STATUS=FAIL
  exit 1
fi
echo 'P1-ROLE-ADMIN-TABLE=PASS scope=audit.audit_events DELETE only; audit.audit_events exists for migration role'

admin_output="$(mktemp)"
runtime_output="$(mktemp)"
if psql "$PSQL_ADMIN_DSN" --no-psqlrc --tuples-only --no-align --command 'SELECT current_user' >"$admin_output" 2>&1 \
  && psql "$PSQL_RUNTIME_DSN" --no-psqlrc --tuples-only --no-align --command 'SELECT current_user' >"$runtime_output" 2>&1; then
  admin_user="$(tr -d '[:space:]' < "$admin_output")"
  runtime_user="$(tr -d '[:space:]' < "$runtime_output")"
  rm -f "$admin_output" "$runtime_output"
else
  echo 'P1-ROLE=FAIL current_user probe failed:' >&2
  redact_file "$admin_output" >&2
  redact_file "$runtime_output" >&2
  rm -f "$admin_output" "$runtime_output"
  P1_ROLE_STATUS=FAIL
  exit 1
fi
if [[ "$admin_user" != 'sentinel_admin' || "$runtime_user" != 'sentinel_app' ]]; then
  echo "P1-ROLE=FAIL current_user mismatch admin=$admin_user runtime=$runtime_user" >&2
  P1_ROLE_STATUS=FAIL
  exit 1
fi
allowed_output="$(mktemp)"
if psql "$PSQL_RUNTIME_DSN" --no-psqlrc --set=ON_ERROR_STOP=1 \
  --command 'SELECT count(*) FROM audit.audit_events' >"$allowed_output" 2>&1; then
  rm -f "$allowed_output"
else
  echo 'P1-ROLE=FAIL runtime SELECT on audit.audit_events failed:' >&2
  redact_file "$allowed_output" >&2
  rm -f "$allowed_output"
  P1_ROLE_STATUS=FAIL
  exit 1
fi
echo 'P1-ROLE-RUNTIME-SELECT=PASS scope=audit.audit_events DELETE only; runtime role performed allowed SELECT on audit.audit_events'

delete_probe="$(mktemp)"
if psql "$PSQL_RUNTIME_DSN" --no-psqlrc --set=ON_ERROR_STOP=1 --set=VERBOSITY=verbose \
  --command 'DELETE FROM audit.audit_events' >"$delete_probe" 2>&1; then
  echo 'P1-ROLE=FAIL runtime DELETE on audit.audit_events unexpectedly succeeded' >&2
  rm -f "$delete_probe"
  P1_ROLE_STATUS=FAIL
  exit 1
fi
if grep -Eq '(^|[[:space:]])42501:' "$delete_probe" && grep -qi 'permission denied' "$delete_probe"; then
  P1_ROLE_STATUS=PASS
  echo 'P1-ROLE-DELETE=PASS scope=audit.audit_events DELETE only; runtime DELETE rejected with SQLSTATE 42501 permission denied'
elif grep -qi 'append-only' "$delete_probe"; then
  echo 'P1-ROLE=FAIL DELETE was rejected by append-only trigger, not privilege SQLSTATE 42501' >&2
  redact_file "$delete_probe" >&2
  rm -f "$delete_probe"
  P1_ROLE_STATUS=FAIL
  exit 1
else
  echo 'P1-ROLE=FAIL DELETE rejection was not SQLSTATE 42501 permission denied:' >&2
  redact_file "$delete_probe" >&2
  rm -f "$delete_probe"
  P1_ROLE_STATUS=FAIL
  exit 1
fi
rm -f "$delete_probe"

echo '== integration contract =='
integration_output="$(mktemp)"
if RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration >"$integration_output" 2>&1; then
  integration_status=0
else
  integration_status=$?
fi
redact_file "$integration_output"
if [[ "$integration_status" -ne 0 ]]; then
  echo 'P1-INTEGRATION=FAIL scope=env-presence contract only; no DB/Redis connection; pytest returned a non-zero status' >&2
  rm -f "$integration_output"
  P1_INTEGRATION_STATUS=FAIL
  exit "$integration_status"
fi
if grep -Eq '(^|[[:space:]])[1-9][0-9]* skipped([,[:space:]]|$)' "$integration_output"; then
  echo 'P1-INTEGRATION=FAIL scope=env-presence contract only; no DB/Redis connection; at least one test was skipped' >&2
  rm -f "$integration_output"
  P1_INTEGRATION_STATUS=FAIL
  exit 1
fi
rm -f "$integration_output"
P1_INTEGRATION_STATUS=PASS
echo 'P1-INTEGRATION=PASS scope=env-presence contract only; no DB/Redis connection; no tests skipped'

echo '== synthetic webhook guard =='
uv run python - <<'PY'
import secrets

from app.core.webhook_guard import is_valid_webhook, validate_secret_config

expected = secrets.token_urlsafe(32)
validate_secret_config(expected)
assert is_valid_webhook(expected, expected)
assert not is_valid_webhook(secrets.token_urlsafe(32), expected)
print("P1-WEBHOOK-GUARD=PASS scope=function-level, no HTTP; is_valid_webhook with job-only random secret")
PY
P1_WEBHOOK_GUARD_STATUS=PASS
echo 'P1-WEBHOOK-DELIVERY=BLOCKED scope=real Telegram delivery; synthetic token is settings-load-only; no Telegram contact; outside PR1 and no real bot token'

echo '== scenario coverage not implemented in PR1 =='
echo 'P1-RACE=BLOCKED no concurrent form-consume integration test exists in tests/'
echo 'P1-REDIS-WORKERS=BLOCKED no two-worker outbox/reclaim integration test exists in tests/'
echo 'P1-RESTORE=BLOCKED no restore integration test/evidence harness exists in tests/'
