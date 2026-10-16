#!/bin/sh
set -eu
: "${SENTINEL_APP_PASSWORD:?SENTINEL_APP_PASSWORD must be set}"
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=ON_ERROR_STOP=1 --set=app_password="$SENTINEL_APP_PASSWORD" <<'SQL'
SELECT format(
  'CREATE ROLE sentinel_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L',
  :'app_password'
) \gexec
SQL
