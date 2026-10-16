#!/usr/bin/env bash
set -euo pipefail
# Operator runbook skeleton. The provider-specific restore command is supplied as
# an executable plus newline-delimited arguments. Each line in RESTORE_ARGS is one
# argument, so spaces and shell metacharacters are passed literally without
# shell-string evaluation.
: "${RESTORE_EXECUTABLE:?Set RESTORE_EXECUTABLE to a verified restore executable}"
if [[ -z "$RESTORE_EXECUTABLE" ]]; then
    printf 'RESTORE_EXECUTABLE must not be empty.\n' >&2
    exit 2
fi
if ! RESTORE_PATH=$(command -v -- "$RESTORE_EXECUTABLE"); then
    printf 'restore executable was not found: %s\n' "$RESTORE_EXECUTABLE" >&2
    exit 2
fi
if [[ ! -x "$RESTORE_PATH" ]]; then
    printf 'restore executable is not executable: %s\n' "$RESTORE_PATH" >&2
    exit 2
fi
restore_args=()
if [[ -n "${RESTORE_ARGS:-}" ]]; then
    while IFS= read -r argument || [[ -n "$argument" ]]; do
        restore_args+=("$argument")
    done <<< "$RESTORE_ARGS"
fi
echo "Restoring into disposable database..."
"$RESTORE_PATH" "${restore_args[@]}"
uv run alembic upgrade head
printf 'Restore drill completed. Record duration, row counts, and checksum in the incident log.\n'
