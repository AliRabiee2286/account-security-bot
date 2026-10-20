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
P1_ROLE_AUDIT_STATUS=NOT_RUN
P1_ROLE_PRIVILEGES_STATUS=NOT_RUN
P1_INTEGRATION_STATUS=NOT_RUN
P1_WEBHOOK_GUARD_STATUS=NOT_RUN
P1_WEBHOOK_DELIVERY_STATUS=BLOCKED
P1_RACE_STATUS=NOT_RUN
P1_REDIS_WORKERS_STATUS=BLOCKED
P1_RESTORE_STATUS=BLOCKED

P1_ROLE_SCOPE='runtime role: DELETE denied (42501) on audit + 4 sensitive tables; catalog sweep over all app-schema tables: no DELETE/TRUNCATE, no UPDATE on audit; no CREATE on schemas; role attributes restricted'
P1_REDIS_WORKERS_SCOPE='claim/lease/reclaim semantics; lease ownership not measured (SEC-004); test-only handler; no production handler'

redact_file() {
  sed -E \
    -e 's#postgresql\+asyncpg://[^[:space:]@]+@#postgresql+asyncpg://<redacted>@#g' \
    -e 's#postgresql://[^[:space:]@]+@#postgresql://<redacted>@#g' \
    -e 's#redis://[^[:space:]@]+@#redis://<redacted>@#g' \
    -e 's#([Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Tt][Oo][Kk][Ee][Nn]|[Ss][Ee][Cc][Rr][Ee][Tt])=[^[:space:]]+#\1=<redacted>#g' \
    "$1"
}

print_pytest_diagnostic() {
  local group_name="$1"
  local pytest_status="$2"
  local report_status="$3"
  local pytest_output="$4"
  local junit_summary="$5"
  printf '%s-DIAGNOSTIC=pytest_exit=%s xml_exit=%s\n' \
    "$group_name" "$pytest_status" "$report_status"
  if [[ -s "$junit_summary" ]]; then
    redact_file "$junit_summary"
  else
    echo "$group_name-XML tests=unknown skipped=unknown errors=unknown failures=unknown"
  fi
  echo "$group_name-PYTEST-TAIL-BEGIN"
  if [[ -s "$pytest_output" ]]; then
    redact_file "$pytest_output" | tail -n 20
  else
    echo '<no pytest output>'
  fi
  echo "$group_name-PYTEST-TAIL-END"
}

run_pytest_group() (
  if [[ "$#" -lt 3 ]]; then
    echo 'run_pytest_group: requires a group label, minimum test count and test files' >&2
    exit 1
  fi
  group_name="$1"
  minimum_tests="$2"
  shift 2
  if [[ ! "$group_name" =~ ^[A-Z][A-Z0-9-]*$ || ! "$minimum_tests" =~ ^[1-9][0-9]*$ ]]; then
    echo 'run_pytest_group: invalid group label or minimum test count' >&2
    exit 1
  fi
  for test_file in "$@"; do
    if [[ "$test_file" == -* || "$test_file" != *.py || ! -f "$test_file" ]]; then
      echo "$group_name-DIAGNOSTIC=invalid or missing test file" >&2
      exit 1
    fi
  done

  pytest_output=""
  junit_path=""
  junit_summary=""
  trap 'rm -f -- "$pytest_output" "$junit_path" "$junit_summary" >/dev/null 2>&1' EXIT
  trap 'exit 1' HUP INT TERM
  pytest_output="$(mktemp 2>/dev/null)" || exit 1
  junit_path="$(mktemp 2>/dev/null)" || exit 1
  junit_summary="$(mktemp 2>/dev/null)" || exit 1

  pytest_status=0
  RUN_INTEGRATION=1 uv run pytest -q -rfE --tb=no --show-capture=no \
    --junitxml="$junit_path" "$@" >"$pytest_output" 2>&1 || pytest_status=$?

  report_status=0
  uv run python - "$junit_path" "$group_name" "$minimum_tests" >"$junit_summary" 2>/dev/null <<'PY' || report_status=$?
import sys
import xml.etree.ElementTree as ET


def report_count(element, key):
    value = element.attrib[key]
    if not value.isascii() or not value.isdecimal():
        raise ValueError
    return int(value)


try:
    root = ET.parse(sys.argv[1]).getroot()
    group_name = sys.argv[2]
    minimum_tests = int(sys.argv[3])
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    if root.tag not in {"testsuite", "testsuites"} or not suites:
        raise ValueError
    if len(list(root.iter("testsuite"))) != len(suites):
        raise ValueError
    if len(list(root.iter("testsuites"))) != int(root.tag == "testsuites"):
        raise ValueError
    tests = skipped = errors = failures = 0
    for suite in suites:
        counts = {key: report_count(suite, key) for key in ("tests", "skipped", "errors", "failures")}
        cases = suite.findall("testcase")
        if counts["tests"] != len(cases):
            raise ValueError
        if any(not case.get("name", "").strip() or not case.get("classname", "").strip() for case in cases):
            raise ValueError
        tests += counts["tests"]
        skipped += counts["skipped"]
        errors += counts["errors"]
        failures += counts["failures"]
    print(f"{group_name}-XML tests={tests} skipped={skipped} errors={errors} failures={failures}")
    if (
        tests < minimum_tests
        or len(list(root.iter("testcase"))) != tests
        or any(count != 0 for count in (skipped, errors, failures))
        or any(list(root.iter(tag)) for tag in ("skipped", "error", "failure"))
    ):
        raise SystemExit(1)
    if root.tag == "testsuites":
        for key, expected in (("tests", tests), ("skipped", 0), ("errors", 0), ("failures", 0)):
            if key in root.attrib and report_count(root, key) != expected:
                raise ValueError
except (OSError, ET.ParseError, KeyError, ValueError, TypeError):
    print(f"{sys.argv[2]}-XML tests=unknown skipped=unknown errors=unknown failures=unknown")
    raise SystemExit(1)
PY

  print_pytest_diagnostic "$group_name" "$pytest_status" "$report_status" \
    "$pytest_output" "$junit_summary"
  [[ "$report_status" -eq 0 ]] || exit 1
  exit "$pytest_status"
)

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
      printf '%s\n\n' '## STG-001 staging gate'
      printf 'Result: %s — %s gates BLOCKED/NOT_RUN\n\n' "$result" "$blocked_count"
      printf '%s\n' '| Gate | Result | Scope |'
      printf '%s\n' '|---|---|---|'
      printf '| P1-LOCK | %s | locked dependency check |\n' "$P1_LOCK_STATUS"
      printf '| P1-SERVICE-HEALTH | %s | PostgreSQL and Redis TCP health |\n' "$P1_SERVICE_HEALTH_STATUS"
      printf '| P1-OFFLINE | %s | static/offline quality checks |\n' "$P1_OFFLINE_STATUS"
      printf '| P1-SECURITY | %s | independent two-reviewer runtime review |\n' "$P1_SECURITY_STATUS"
      printf '| P1-DB | %s | empty database migration and head check |\n' "$P1_DB_STATUS"
      printf '| P1-ROLE | %s | %s |\n' "$P1_ROLE_STATUS" "$P1_ROLE_SCOPE"
      printf '| P1-INTEGRATION | %s | real PostgreSQL + Redis round-trip |\n' "$P1_INTEGRATION_STATUS"
      printf '| P1-WEBHOOK-GUARD | %s | function-level, no HTTP |\n' "$P1_WEBHOOK_GUARD_STATUS"
      printf '| P1-WEBHOOK-DELIVERY | %s | real Telegram delivery; synthetic token only loads Settings; no Telegram contact; outside PR1 |\n' "$P1_WEBHOOK_DELIVERY_STATUS"
      printf '| P1-RACE | %s | one-time form consume; 20 barrier-synchronized pairs + 1 lock-wait overlap case, exactly one winner each; PostgreSQL; no HTTP |\n' "$P1_RACE_STATUS"
      printf '| P1-REDIS-WORKERS | %s | %s |\n' "$P1_REDIS_WORKERS_STATUS" "$P1_REDIS_WORKERS_SCOPE"
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
  P1_ROLE_AUDIT_STATUS=PASS
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

echo '== runtime role privilege catalog =='
if run_pytest_group P1-ROLE-PRIVILEGES 2 tests/integration/test_runtime_role_privileges.py; then
  P1_ROLE_PRIVILEGES_STATUS=PASS
else
  role_privileges_status=$?
  P1_ROLE_PRIVILEGES_STATUS=FAIL
  P1_ROLE_STATUS=FAIL
  echo "P1-ROLE=FAIL scope=$P1_ROLE_SCOPE" >&2
  if [[ "$role_privileges_status" -eq 0 ]]; then
    role_privileges_status=1
  fi
  exit "$role_privileges_status"
fi

if [[ "$P1_ROLE_AUDIT_STATUS" == PASS && "$P1_ROLE_PRIVILEGES_STATUS" == PASS ]]; then
  P1_ROLE_STATUS=PASS
  echo "P1-ROLE=PASS scope=$P1_ROLE_SCOPE"
else
  P1_ROLE_STATUS=FAIL
  echo "P1-ROLE=FAIL scope=$P1_ROLE_SCOPE" >&2
  exit 1
fi

echo '== real PostgreSQL + Redis round-trip =='
if run_pytest_group P1-INTEGRATION 3 \
  tests/integration/test_gate_contract.py tests/integration/test_runtime_connectivity.py; then
  P1_INTEGRATION_STATUS=PASS
  echo 'P1-INTEGRATION=PASS scope=real PostgreSQL + Redis round-trip; independent pytest; tests>=3; skipped=0; errors=0; failures=0'
else
  connectivity_status=$?
  P1_INTEGRATION_STATUS=FAIL
  echo 'P1-INTEGRATION=FAIL scope=real PostgreSQL + Redis round-trip; independent pytest or structured report check failed' >&2
  exit "$connectivity_status"
fi

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

echo '== one-time form consume race =='
if run_pytest_group P1-RACE 3 tests/integration/test_one_time_form_race.py; then
  P1_RACE_STATUS=PASS
  echo 'P1-RACE=PASS scope=one-time form consume; 20 barrier-synchronized pairs + 1 lock-wait overlap case, exactly one winner each; PostgreSQL; no HTTP'
else
  race_status=$?
  P1_RACE_STATUS=FAIL
  echo 'P1-RACE=FAIL scope=one-time form consume; 20 barrier-synchronized pairs + 1 lock-wait overlap case, exactly one winner each; PostgreSQL; no HTTP' >&2
  exit "$race_status"
fi
echo '== outbox claim/lease/reclaim =='
if run_pytest_group P1-REDIS-WORKERS 2 tests/integration/test_outbox_two_workers.py; then
  P1_REDIS_WORKERS_STATUS=PASS
  echo "P1-REDIS-WORKERS=PASS scope=$P1_REDIS_WORKERS_SCOPE"
else
  outbox_status=$?
  P1_REDIS_WORKERS_STATUS=FAIL
  echo "P1-REDIS-WORKERS=FAIL scope=$P1_REDIS_WORKERS_SCOPE" >&2
  exit "$outbox_status"
fi
echo '== scenario coverage not implemented in PR1 =='
echo 'P1-RESTORE=BLOCKED no restore integration test/evidence harness exists in tests/'
