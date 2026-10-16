#!/usr/bin/env bash
set -euo pipefail
# This gate is runnable without network/dependencies and never claims integration success.
python3 -m compileall -q app tests migrations scripts
python3 scripts/validate_migrations.py
python3 scripts/validate_config.py
python3 scripts/check_model_annotations.py
python3 scripts/validate_migration_semantics.py
python3 scripts/check_module_boundaries.py
python3 scripts/security_invariants.py
python3 scripts/offline_smoke.py
python3 scripts/report_gates.py
if grep -RInE 'print\([^)]*(password|token|secret|seed)|logger\.(info|warning|error)\([^)]*(password|token|secret|seed)' app --include='*.py'; then
  echo 'Potential secret logging found' >&2; exit 1
fi
printf 'Static gate passed; environment gates remain authoritative.\n'
