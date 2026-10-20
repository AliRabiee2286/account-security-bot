"""Runtime and migration-role privilege checks against disposable PostgreSQL."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import asyncpg
import pytest
from sqlalchemy.engine import make_url

CONNECT_TIMEOUT = 5
QUERY_TIMEOUT = 5
CLEANUP_TIMEOUT = 3

APP_SCHEMAS = ("core", "identity", "audit", "mailboxes", "social", "incidents")
SENSITIVE_CHECKS = (
    (
        ("social", "credentials"),
        "SELECT 1 FROM social.credentials LIMIT 1",
        "DELETE FROM social.credentials WHERE false",
    ),
    (
        ("identity", "sessions"),
        "SELECT 1 FROM identity.sessions LIMIT 1",
        "DELETE FROM identity.sessions WHERE false",
    ),
    (
        ("identity", "mfa_credentials"),
        "SELECT 1 FROM identity.mfa_credentials LIMIT 1",
        "DELETE FROM identity.mfa_credentials WHERE false",
    ),
    (
        ("identity", "approval_requests"),
        "SELECT 1 FROM identity.approval_requests LIMIT 1",
        "DELETE FROM identity.approval_requests WHERE false",
    ),
)
SENSITIVE_TABLES = tuple(check[0] for check in SENSITIVE_CHECKS)
ROLE_ATTRIBUTES = ("rolsuper", "rolcreaterole", "rolcreatedb", "rolbypassrls", "rolreplication")

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="requires PostgreSQL and RUN_INTEGRATION=1",
)


CATALOG_QUERY = """
SELECT
    n.nspname AS schema_name,
    c.relname AS table_name,
    has_table_privilege('sentinel_app', c.oid, 'DELETE') AS can_delete,
    has_table_privilege('sentinel_app', c.oid, 'TRUNCATE') AS can_truncate,
    has_table_privilege('sentinel_app', c.oid, 'UPDATE') AS can_update
FROM pg_namespace AS n
JOIN pg_class AS c ON c.relnamespace = n.oid
WHERE n.nspname = ANY($1::text[])
  AND c.relkind IN ('r', 'p')
ORDER BY n.nspname, c.relname
"""

SCHEMA_PRIVILEGE_QUERY = """
SELECT
    n.nspname AS schema_name,
    has_schema_privilege('sentinel_app', n.oid, 'CREATE') AS can_create
FROM pg_namespace AS n
WHERE n.nspname = ANY($1::text[])
ORDER BY n.nspname
"""

ROLE_QUERY = """
SELECT
    app.rolname,
    app.rolsuper,
    app.rolcreaterole,
    app.rolcreatedb,
    app.rolbypassrls,
    app.rolreplication,
    EXISTS (
        SELECT 1
        FROM pg_auth_members AS membership
        WHERE membership.member = app.oid
          AND membership.roleid = app_role.oid
    ) AS is_member
FROM pg_roles AS app
JOIN pg_roles AS app_role ON app_role.rolname = 'sentinel_app_role'
WHERE app.rolname = 'sentinel_app'
"""

DATABASE_IDENTITY_QUERY = """
SELECT current_database() AS database_name, current_user, session_user
"""


def _connection_dsn(environment_name: str, expected_role: str) -> str | None:
    raw_url = os.getenv(environment_name, "").strip()
    if not raw_url:
        return None
    try:
        parsed = make_url(raw_url)
        if parsed.drivername not in {"postgres", "postgresql", "postgresql+asyncpg"}:
            return None
        if parsed.username != expected_role:
            return None
        return parsed.set(drivername="postgresql").render_as_string(hide_password=False)
    except Exception:
        return None


async def _close_connection(connection: asyncpg.Connection) -> bool:
    try:
        async with asyncio.timeout(CLEANUP_TIMEOUT):
            await connection.close(timeout=CLEANUP_TIMEOUT)
    except Exception:
        return False
    return True


async def _connect(environment_name: str, expected_role: str) -> asyncpg.Connection:
    dsn = _connection_dsn(environment_name, expected_role)
    if dsn is None:
        pytest.fail("PostgreSQL connection configuration is missing or invalid", pytrace=False)

    connection: asyncpg.Connection | None = None
    verified = False
    try:
        async with asyncio.timeout(CONNECT_TIMEOUT):
            connection = await asyncpg.connect(
                dsn=dsn,
                timeout=CONNECT_TIMEOUT,
                command_timeout=QUERY_TIMEOUT,
                server_settings={
                    "statement_timeout": str(QUERY_TIMEOUT * 1000),
                    "lock_timeout": str(QUERY_TIMEOUT * 1000),
                    "idle_in_transaction_session_timeout": str(
                        (QUERY_TIMEOUT + CLEANUP_TIMEOUT) * 1000
                    ),
                },
            )
            async with asyncio.timeout(QUERY_TIMEOUT):
                identity = await connection.fetchrow("SELECT current_user, session_user")
            verified = (
                identity is not None
                and identity["current_user"] == expected_role
                and identity["session_user"] == expected_role
            )
    except Exception:
        verified = False

    if connection is None or not verified:
        closed = connection is None or await _close_connection(connection)
        if not closed:
            pytest.fail("PostgreSQL connection cleanup failed", pytrace=False)
        pytest.fail("PostgreSQL connection or role verification failed", pytrace=False)
    return connection


@pytest.fixture
async def runtime_connection() -> AsyncIterator[asyncpg.Connection]:
    connection = await _connect("DATABASE_URL", "sentinel_app")
    try:
        yield connection
    finally:
        if not await _close_connection(connection):
            pytest.fail("Runtime PostgreSQL connection cleanup failed", pytrace=False)


@pytest.fixture
async def admin_connection() -> AsyncIterator[asyncpg.Connection]:
    connection = await _connect("MIGRATION_DATABASE_URL", "sentinel_admin")
    try:
        yield connection
    finally:
        if not await _close_connection(connection):
            pytest.fail("Admin PostgreSQL connection cleanup failed", pytrace=False)


async def _select_succeeds(connection: asyncpg.Connection, query: str) -> bool:
    try:
        async with asyncio.timeout(QUERY_TIMEOUT):
            await connection.fetch(query)
    except Exception:
        return False
    return True


async def _delete_is_denied(connection: asyncpg.Connection, query: str) -> bool:
    transaction = connection.transaction()
    sqlstate: str | None = None
    failed = False
    try:
        async with asyncio.timeout(QUERY_TIMEOUT):
            await transaction.start()
            try:
                await connection.execute(query)
            except asyncpg.PostgresError as error:
                sqlstate = error.sqlstate
            except Exception:
                failed = True
            else:
                failed = True
    except Exception:
        failed = True
    finally:
        try:
            async with asyncio.timeout(CLEANUP_TIMEOUT):
                await transaction.rollback()
        except Exception:
            failed = True
    return not failed and sqlstate == "42501"


async def test_runtime_role_selects_and_rejects_deletes(
    runtime_connection: asyncpg.Connection,
) -> None:
    select_failures = [
        ".".join(table)
        for table, select_query, _ in SENSITIVE_CHECKS
        if not await _select_succeeds(runtime_connection, select_query)
    ]
    delete_failures = [
        ".".join(table)
        for table, _, delete_query in SENSITIVE_CHECKS
        if not await _delete_is_denied(runtime_connection, delete_query)
    ]

    if len(SENSITIVE_CHECKS) != len(SENSITIVE_TABLES) or select_failures:
        if select_failures:
            print("runtime SELECT privilege violation tables: " + ", ".join(select_failures))
        pytest.fail("Runtime SELECT privilege checks failed", pytrace=False)
    if delete_failures:
        print("runtime DELETE privilege violation tables: " + ", ".join(delete_failures))
        pytest.fail("Runtime DELETE privilege checks failed", pytrace=False)


async def test_admin_catalog_confirms_runtime_role_privileges(
    admin_connection: asyncpg.Connection,
    runtime_connection: asyncpg.Connection,
) -> None:
    rows: list[asyncpg.Record] | None = None
    schema_rows: list[asyncpg.Record] | None = None
    role: asyncpg.Record | None = None
    admin_identity: asyncpg.Record | None = None
    runtime_identity: asyncpg.Record | None = None
    query_failed = False
    try:
        async with asyncio.timeout(QUERY_TIMEOUT):
            rows = await admin_connection.fetch(CATALOG_QUERY, list(APP_SCHEMAS))
            schema_rows = await admin_connection.fetch(SCHEMA_PRIVILEGE_QUERY, list(APP_SCHEMAS))
            role = await admin_connection.fetchrow(ROLE_QUERY)
            admin_identity = await admin_connection.fetchrow(DATABASE_IDENTITY_QUERY)
            runtime_identity = await runtime_connection.fetchrow(DATABASE_IDENTITY_QUERY)
    except Exception:
        query_failed = True

    if (
        query_failed
        or rows is None
        or schema_rows is None
        or role is None
        or admin_identity is None
        or runtime_identity is None
    ):
        pytest.fail("Admin PostgreSQL privilege catalog query failed", pytrace=False)

    returned_tables = {(row["schema_name"], row["table_name"]) for row in rows}
    expected_tables = set(SENSITIVE_TABLES) | {("audit", "audit_events")}
    minimum_table_count = len(APP_SCHEMAS)
    if len(rows) < minimum_table_count or not expected_tables.issubset(returned_tables):
        pytest.fail("Admin PostgreSQL privilege catalog is incomplete", pytrace=False)

    returned_schemas = {row["schema_name"] for row in schema_rows}
    schema_create_violations = {row["schema_name"] for row in schema_rows if row["can_create"]}
    table_violations = {
        f"{row['schema_name']}.{row['table_name']}"
        for row in rows
        if row["can_delete"]
        or row["can_truncate"]
        or (row["schema_name"] == "audit" and row["can_update"])
    }
    role_attribute_violations = sum(bool(role[attribute]) for attribute in ROLE_ATTRIBUTES)
    role_membership_violation = not role["is_member"]
    database_identity_violation = (
        admin_identity["database_name"] != runtime_identity["database_name"]
        or admin_identity["current_user"] != "sentinel_admin"
        or admin_identity["session_user"] != "sentinel_admin"
        or runtime_identity["current_user"] != "sentinel_app"
        or runtime_identity["session_user"] != "sentinel_app"
    )

    print(
        "admin privilege catalog: "
        f"table_count={len(rows)}, "
        f"table_violation_count={len(table_violations)}, "
        f"schema_count={len(returned_schemas)}, "
        f"schema_create_violation_count={len(schema_create_violations)}, "
        f"role_attribute_violation_count={role_attribute_violations}, "
        f"role_membership_violation={int(role_membership_violation)}, "
        f"database_identity_violation={int(database_identity_violation)}"
    )
    if table_violations:
        print("admin privilege violation tables: " + ", ".join(sorted(table_violations)))
    if schema_create_violations:
        print(
            "admin schema CREATE violation schemas: " + ", ".join(sorted(schema_create_violations))
        )

    if table_violations:
        pytest.fail("Runtime role has forbidden table privileges", pytrace=False)
    if returned_schemas != set(APP_SCHEMAS):
        pytest.fail("Admin PostgreSQL privilege catalog is missing app schemas", pytrace=False)
    if schema_create_violations:
        pytest.fail("Runtime role has forbidden schema privileges", pytrace=False)
    if role_attribute_violations:
        pytest.fail("Runtime role has forbidden role attributes", pytrace=False)
    if role_membership_violation:
        pytest.fail("Runtime role is not a member of sentinel_app_role", pytrace=False)
    if database_identity_violation:
        pytest.fail(
            "Runtime and admin connections target different roles or databases",
            pytrace=False,
        )
