"""Logical PostgreSQL 16 dump/restore checks for the disposable staging gate."""

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import subprocess
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Final
from uuid import UUID, uuid4

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy.engine import URL, make_url

EXPECTED_MIGRATION_HEAD: Final = "0007"
POSTGRES_CONTAINER_ENV: Final = "RESTORE_POSTGRES_CONTAINER"
SUBPROCESS_TIMEOUT: Final = 90
QUERY_TIMEOUT: Final = 10
APP_SCHEMAS: Final = ("audit", "core", "identity", "mailboxes", "social", "incidents")
AUDIT_TRIGGER_NAMES: Final = frozenset({"trg_audit_no_update", "trg_audit_no_truncate"})
CONTAINER_NAME_PATTERN: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")

pytestmark = [
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION") != "1",
        reason="requires RUN_INTEGRATION=1 and a disposable PostgreSQL 16 container",
    ),
    pytest.mark.asyncio(loop_scope="module"),
]


@dataclass(frozen=True)
class CommandResult:
    returncode: int | None
    stdout: str
    exception_type: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0 and self.exception_type is None


@dataclass(frozen=True)
class TableState:
    row_count: int
    digest: str


@dataclass
class RestoreContext:
    container: str
    source_database: str
    source_connection: asyncpg.Connection
    dump_path: str
    target_database: str
    target_connection: asyncpg.Connection
    source_tables: tuple[tuple[str, str], ...]
    source_snapshot: dict[tuple[str, str], TableState]
    non_audit_ids: dict[str, UUID | str]
    extra_target_databases: set[str] = field(default_factory=set)
    round_trip_verified: bool = False


class RestoreCheckError(Exception):
    """Sanitized internal failure used before converting a DB error to pytest output."""


def _command_result(args: list[str]) -> CommandResult:
    """Run one bounded subprocess without exposing stdout/stderr to pytest output."""
    try:
        completed = subprocess.run(  # noqa: S603 - command and arguments are an internal list
            args,
            capture_output=True,
            check=False,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return CommandResult(None, "", "TimeoutExpired")
    except OSError as error:
        return CommandResult(None, "", type(error).__name__)
    return CommandResult(completed.returncode, completed.stdout)


def _command_diagnostic(label: str, result: CommandResult) -> str:
    if result.exception_type is not None:
        return f"{label} failed; exception_type={result.exception_type}"
    return f"{label} failed; exit_code={result.returncode}"


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _qualified_table_name(schema: str, table: str) -> str:
    return f"{_quote_identifier(schema)}.{_quote_identifier(table)}"


def _require_container(container: str) -> None:
    if not CONTAINER_NAME_PATTERN.fullmatch(container):
        pytest.fail(
            "Restore PostgreSQL container name is invalid; error_type=container-name", pytrace=False
        )
    result = _command_result(["docker", "inspect", "--format", "{{.State.Running}}", container])
    if not result.succeeded or result.stdout.strip() != "true":
        pytest.fail(
            "Restore PostgreSQL container is unavailable; error_type=container-unavailable",
            pytrace=False,
        )


def _admin_url() -> tuple[URL, str]:
    raw_url = os.getenv("MIGRATION_DATABASE_URL", "").strip()
    if not raw_url:
        pytest.fail(
            "Missing restore integration environment: MIGRATION_DATABASE_URL", pytrace=False
        )
    try:
        parsed = make_url(raw_url)
    except Exception as error:
        pytest.fail(
            f"Restore admin database URL is invalid; exception_type={type(error).__name__}",
            pytrace=False,
        )
    if parsed.drivername not in {"postgres", "postgresql", "postgresql+asyncpg"}:
        pytest.fail(
            "Restore admin database URL has an unsupported driver; error_type=driver", pytrace=False
        )
    if parsed.username != "sentinel_admin" or not parsed.database:
        pytest.fail(
            "Restore admin database URL must use sentinel_admin; error_type=role-or-database",
            pytrace=False,
        )
    return parsed, parsed.set(drivername="postgresql").render_as_string(hide_password=False)


async def _connect_admin(dsn: str, stage: str) -> asyncpg.Connection:
    try:
        async with asyncio.timeout(QUERY_TIMEOUT):
            return await asyncpg.connect(
                dsn=dsn,
                timeout=QUERY_TIMEOUT,
                command_timeout=QUERY_TIMEOUT,
                server_settings={
                    "statement_timeout": str(QUERY_TIMEOUT * 1000),
                    "lock_timeout": str(QUERY_TIMEOUT * 1000),
                },
            )
    except BaseException as error:
        pytest.fail(f"{stage} failed; exception_type={type(error).__name__}", pytrace=False)
        raise AssertionError("unreachable") from error


async def _close_connection(connection: asyncpg.Connection | None) -> str | None:
    if connection is None:
        return None
    try:
        async with asyncio.timeout(QUERY_TIMEOUT):
            await connection.close(timeout=QUERY_TIMEOUT)
    except BaseException as error:
        return type(error).__name__
    return None


async def _database_exists(connection: asyncpg.Connection, database_name: str) -> bool:
    try:
        value = await connection.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname = $1)", database_name
        )
    except BaseException as error:
        pytest.fail(
            f"Database existence check failed; exception_type={type(error).__name__}", pytrace=False
        )
        return False
    return bool(value)


def _create_database(container: str, database_name: str) -> None:
    result = _command_result(
        [
            "docker",
            "exec",
            container,
            "createdb",
            "-U",
            "sentinel_admin",
            "--template",
            "template0",
            database_name,
        ]
    )
    if not result.succeeded:
        pytest.fail(_command_diagnostic("createdb", result), pytrace=False)


def _drop_database(container: str, database_name: str) -> str | None:
    result = _command_result(
        [
            "docker",
            "exec",
            container,
            "dropdb",
            "-U",
            "sentinel_admin",
            "--if-exists",
            database_name,
        ]
    )
    if result.succeeded:
        return None
    return result.exception_type or f"exit_code={result.returncode}"


def _dump_exists(container: str, dump_path: str) -> bool:
    result = _command_result(["docker", "exec", container, "test", "-f", dump_path])
    return result.succeeded


def _remove_dump(container: str, dump_path: str) -> str | None:
    result = _command_result(["docker", "exec", container, "rm", "-f", dump_path])
    if result.succeeded:
        return None
    return result.exception_type or f"exit_code={result.returncode}"


async def _table_names(connection: asyncpg.Connection) -> tuple[tuple[str, str], ...]:
    rows = await connection.fetch(
        """
        SELECT n.nspname AS schema_name, c.relname AS table_name
          FROM pg_class AS c
          JOIN pg_namespace AS n ON n.oid = c.relnamespace
         WHERE n.nspname = ANY($1::text[])
           AND c.relkind IN ('r', 'p')
         ORDER BY n.nspname, c.relname
        """,
        list(APP_SCHEMAS),
    )
    tables = {(str(row["schema_name"]), str(row["table_name"])) for row in rows}
    has_alembic_version = await connection.fetchval(
        "SELECT to_regclass('public.alembic_version') IS NOT NULL"
    )
    if has_alembic_version:
        tables.add(("public", "alembic_version"))
    return tuple(sorted(tables))


async def _table_state(connection: asyncpg.Connection, table: tuple[str, str]) -> TableState:
    qualified_name = _qualified_table_name(*table)
    row = await connection.fetchrow(
        f"""
        SELECT count(*)::bigint AS row_count,
               md5(COALESCE(string_agg(row_text, '|' ORDER BY row_text), '')) AS digest
          FROM (
                SELECT row_to_json(t)::text AS row_text
                  FROM {qualified_name} AS t
               ) AS rows
        """  # noqa: S608 - identifiers are quoted from database metadata
    )
    if row is None:
        raise RestoreCheckError("no-row")
    return TableState(row_count=int(row["row_count"]), digest=str(row["digest"]))


async def _snapshot(
    connection: asyncpg.Connection, tables: tuple[tuple[str, str], ...]
) -> dict[tuple[str, str], TableState]:
    snapshot: dict[tuple[str, str], TableState] = {}
    for table in tables:
        try:
            snapshot[table] = await _table_state(connection, table)
        except RestoreCheckError as error:
            pytest.fail(
                f"Table state query failed; table={table[0]}.{table[1]}; error_type={error}",
                pytrace=False,
            )
        except Exception as error:
            pytest.fail(
                "Table state query failed; "
                f"table={table[0]}.{table[1]}; exception_type={type(error).__name__}",
                pytrace=False,
            )
    return snapshot


async def _migration_head(connection: asyncpg.Connection, stage: str) -> str:
    try:
        value = await connection.fetchval("SELECT version_num FROM public.alembic_version")
    except Exception as error:
        pytest.fail(f"{stage} failed; exception_type={type(error).__name__}", pytrace=False)
        return ""
    if value is None:
        pytest.fail(f"{stage} failed; error_type=missing-migration-head", pytrace=False)
    return str(value)


async def _seed_synthetic_rows(connection: asyncpg.Connection) -> dict[str, UUID | str]:
    department_id = uuid4()
    outbox_id = uuid4()
    subject_id = uuid4()
    owner_id = uuid4()
    token_hash = secrets.token_hex(32)
    audit_id = uuid4()
    try:
        await connection.execute(
            "INSERT INTO identity.departments (id, name) VALUES ($1, $2)",
            department_id,
            f"PR2-E synthetic {department_id}",
        )
        await connection.execute(
            """
            INSERT INTO core.outbox (
                id, event_type, payload, request_id, status, attempts,
                available_at, delivered_at, delivering_at
            )
            VALUES ($1, $2, $3::jsonb, $4, 'delivered', 1, now(), now(), NULL)
            """,
            outbox_id,
            "pr2e.synthetic.restore",
            json.dumps({"synthetic": True, "case": "restore"}, separators=(",", ":")),
            f"pr2e-{outbox_id}",
        )
        await connection.execute(
            """
            INSERT INTO social.one_time_forms (
                token_hash, subject_id, purpose, expires_at, owner_type, owner_id
            )
            VALUES ($1, $2, 'social_oauth', now() + interval '1 hour', 'social_account', $3)
            """,
            token_hash,
            subject_id,
            owner_id,
        )
        await connection.execute(
            """
            INSERT INTO audit.audit_events (
                id, request_id, actor_type, actor_id, action, target_type,
                target_id, result, reason, metadata, prev_hash, row_hash
            )
            VALUES (
                $1, $2, 'system', 'pr2e-synthetic', 'restore.test',
                'restore', $3, 'success', 'synthetic restore evidence',
                $4::jsonb, NULL, $5
            )
            """,
            audit_id,
            f"pr2e-audit-{audit_id}",
            str(subject_id),
            json.dumps({"synthetic": True, "case": "restore"}, separators=(",", ":")),
            secrets.token_hex(32),
        )
    except Exception as error:
        pytest.fail(
            f"Synthetic restore seed failed; exception_type={type(error).__name__}", pytrace=False
        )
    return {
        "department_id": department_id,
        "outbox_id": outbox_id,
        "token_hash": token_hash,
    }


async def _cleanup_non_audit_rows(
    connection: asyncpg.Connection, non_audit_ids: dict[str, UUID | str]
) -> str | None:
    try:
        await connection.execute(
            "DELETE FROM social.one_time_forms WHERE token_hash = $1",
            non_audit_ids["token_hash"],
        )
        await connection.execute(
            "DELETE FROM core.outbox WHERE id = $1", non_audit_ids["outbox_id"]
        )
        await connection.execute(
            "DELETE FROM identity.departments WHERE id = $1", non_audit_ids["department_id"]
        )
    except Exception as error:
        return type(error).__name__
    return None


async def _restore_privilege_violations(
    connection: asyncpg.Connection,
) -> list[tuple[str, str, str]]:
    rows = await connection.fetch(
        """
        SELECT n.nspname AS schema_name,
               c.relname AS table_name,
               has_table_privilege(
                   'sentinel_app', format('%I.%I', n.nspname, c.relname), 'DELETE'
               ) AS can_delete,
               has_table_privilege(
                   'sentinel_app', format('%I.%I', n.nspname, c.relname), 'TRUNCATE'
               ) AS can_truncate,
               has_table_privilege(
                   'sentinel_app', format('%I.%I', n.nspname, c.relname), 'UPDATE'
               ) AS can_update
          FROM pg_class AS c
          JOIN pg_namespace AS n ON n.oid = c.relnamespace
         WHERE n.nspname = ANY($1::text[])
           AND c.relkind IN ('r', 'p')
         ORDER BY n.nspname, c.relname
        """,
        list(APP_SCHEMAS),
    )
    violations: list[tuple[str, str, str]] = []
    for row in rows:
        schema_name = str(row["schema_name"])
        table_name = str(row["table_name"])
        if row["can_delete"]:
            violations.append((schema_name, table_name, "DELETE"))
        if row["can_truncate"]:
            violations.append((schema_name, table_name, "TRUNCATE"))
        if schema_name == "audit" and row["can_update"]:
            violations.append((schema_name, table_name, "UPDATE"))
    return violations


async def _audit_trigger_names(connection: asyncpg.Connection) -> set[str]:
    rows = await connection.fetch(
        """
        SELECT t.tgname
          FROM pg_trigger AS t
          JOIN pg_class AS c ON c.oid = t.tgrelid
          JOIN pg_namespace AS n ON n.oid = c.relnamespace
         WHERE n.nspname = 'audit'
           AND c.relname = 'audit_events'
           AND NOT t.tgisinternal
        """
    )
    return {str(row["tgname"]) for row in rows}


def _target_dsn(parsed_url: URL, database_name: str) -> str:
    return parsed_url.set(database=database_name, drivername="postgresql").render_as_string(
        hide_password=False
    )


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def restore_context() -> AsyncIterator[RestoreContext]:  # noqa: PLR0912, PLR0915
    container = os.getenv(POSTGRES_CONTAINER_ENV, "").strip()
    if not container:
        pytest.fail(
            f"Missing restore integration environment: {POSTGRES_CONTAINER_ENV}",
            pytrace=False,
        )
    _require_container(container)
    parsed_url, admin_dsn = _admin_url()
    source_connection: asyncpg.Connection | None = None
    target_connection: asyncpg.Connection | None = None
    target_database = ""
    dump_path = f"/tmp/pr2e-restore-{secrets.token_hex(16)}.dump"  # noqa: S108 - path is inside the disposable container
    non_audit_ids: dict[str, UUID | str] | None = None
    target_databases: list[str] = []
    cleanup_errors: list[str] = []

    try:
        source_connection = await _connect_admin(admin_dsn, "Source admin connection")
        assert source_connection is not None
        source_database = str(parsed_url.database)
        head = await _migration_head(source_connection, "Source migration head check")
        if head != EXPECTED_MIGRATION_HEAD:
            pytest.fail(
                "Source migration head mismatch; "
                f"expected={EXPECTED_MIGRATION_HEAD}; actual={head}",
                pytrace=False,
            )

        existing_audit_rows = await source_connection.fetchval(
            "SELECT count(*) FROM audit.audit_events"
        )
        if int(existing_audit_rows or 0) != 0:
            pytest.fail(
                "Restore precondition failed; table=audit.audit_events; error_type=non-empty-audit",
                pytrace=False,
            )

        non_audit_ids = await _seed_synthetic_rows(source_connection)
        source_tables = await _table_names(source_connection)
        source_snapshot = await _snapshot(source_connection, source_tables)

        dump_result = _command_result(
            [
                "docker",
                "exec",
                container,
                "pg_dump",
                "--format=custom",
                "--file",
                dump_path,
                "-U",
                "sentinel_admin",
                "-d",
                source_database,
            ]
        )
        if not dump_result.succeeded:
            pytest.fail(_command_diagnostic("pg_dump", dump_result), pytrace=False)
        if not _dump_exists(container, dump_path):
            pytest.fail(
                "pg_dump did not create an in-container dump; error_type=missing-dump",
                pytrace=False,
            )

        target_database = f"pr2e_restore_{secrets.token_hex(8)}"
        target_databases.append(target_database)
        _create_database(container, target_database)
        restore_result = _command_result(
            [
                "docker",
                "exec",
                container,
                "pg_restore",
                "--exit-on-error",
                "-U",
                "sentinel_admin",
                "-d",
                target_database,
                dump_path,
            ]
        )
        if not restore_result.succeeded:
            pytest.exit(
                _command_diagnostic("pg_restore", restore_result),
                returncode=1,
            )

        target_connection = await _connect_admin(
            _target_dsn(parsed_url, target_database), "Target admin connection"
        )
        yield RestoreContext(
            container=container,
            source_database=source_database,
            source_connection=source_connection,
            dump_path=dump_path,
            target_database=target_database,
            target_connection=target_connection,
            source_tables=source_tables,
            source_snapshot=source_snapshot,
            non_audit_ids=non_audit_ids,
            extra_target_databases=set(),
        )
    finally:
        target_close_error = await _close_connection(target_connection)
        if target_close_error is not None:
            cleanup_errors.append(f"target-close:{target_close_error}")
        if target_database:
            target_drop_error = _drop_database(container, target_database)
            if target_drop_error is not None:
                cleanup_errors.append(f"target-drop:{target_drop_error}")
        if non_audit_ids is not None and source_connection is not None:
            source_cleanup_error = await _cleanup_non_audit_rows(source_connection, non_audit_ids)
            if source_cleanup_error is not None:
                cleanup_errors.append(f"source-cleanup:{source_cleanup_error}")
        dump_remove_error = _remove_dump(container, dump_path)
        if dump_remove_error is not None:
            cleanup_errors.append(f"dump-remove:{dump_remove_error}")
        source_close_error = await _close_connection(source_connection)
        if source_close_error is not None:
            cleanup_errors.append(f"source-close:{source_close_error}")
        if cleanup_errors:
            pytest.fail(
                "Restore cleanup failed; error_type=" + ",".join(cleanup_errors),
                pytrace=False,
            )


async def _assert_table_sets_match(
    source_tables: tuple[tuple[str, str], ...], target_tables: tuple[tuple[str, str], ...]
) -> None:
    if source_tables == target_tables:
        return
    source_only = sorted(set(source_tables) - set(target_tables))
    target_only = sorted(set(target_tables) - set(source_tables))
    table = (source_only or target_only or [("unknown", "unknown")])[0]
    mismatch_type = (
        "missing-table" if source_only else "extra-table" if target_only else "table-order"
    )
    pytest.fail(
        f"Restore table set mismatch; table={table[0]}.{table[1]}; error_type={mismatch_type}",
        pytrace=False,
    )


async def test_restore_round_trip_preserves_tables_rows_digests_and_privileges(
    restore_context: RestoreContext,
) -> None:
    target_tables = await _table_names(restore_context.target_connection)
    await _assert_table_sets_match(restore_context.source_tables, target_tables)

    target_head = await _migration_head(
        restore_context.target_connection, "Target migration head check"
    )
    if target_head != EXPECTED_MIGRATION_HEAD:
        pytest.fail(
            "Target migration head mismatch; "
            f"expected={EXPECTED_MIGRATION_HEAD}; actual={target_head}",
            pytrace=False,
        )

    target_snapshot = await _snapshot(restore_context.target_connection, target_tables)
    for table in restore_context.source_tables:
        source_state = restore_context.source_snapshot[table]
        target_state = target_snapshot[table]
        if source_state.row_count != target_state.row_count:
            pytest.fail(
                f"Restore data mismatch; table={table[0]}.{table[1]}; error_type=row-count",
                pytrace=False,
            )
        if source_state.digest != target_state.digest:
            pytest.fail(
                f"Restore data mismatch; table={table[0]}.{table[1]}; error_type=md5-digest",
                pytrace=False,
            )

    privilege_violations = await _restore_privilege_violations(restore_context.target_connection)
    if privilege_violations:
        schema_name, table_name, privilege = privilege_violations[0]
        pytest.fail(
            f"Restore privilege mismatch; table={schema_name}.{table_name}; error_type={privilege}",
            pytrace=False,
        )

    trigger_names = await _audit_trigger_names(restore_context.target_connection)
    missing_triggers = sorted(AUDIT_TRIGGER_NAMES - trigger_names)
    if missing_triggers:
        pytest.fail(
            "Restore audit trigger mismatch; table=audit.audit_events; "
            f"error_type=missing-trigger-{missing_triggers[0]}",
            pytrace=False,
        )

    restore_context.round_trip_verified = True
    print(f"restore round-trip: tables={len(target_tables)} head={target_head} privileges=verified")


async def test_corrupt_dump_fails_and_target_database_is_dropped(
    restore_context: RestoreContext,
) -> None:
    target_database = f"pr2e_corrupt_{secrets.token_hex(8)}"
    restore_context.extra_target_databases.add(target_database)
    restore_result: CommandResult | None = None
    try:
        _create_database(restore_context.container, target_database)
        corrupt_result = _command_result(
            [
                "docker",
                "exec",
                restore_context.container,
                "truncate",
                "-s",
                "1",
                restore_context.dump_path,
            ]
        )
        if not corrupt_result.succeeded:
            pytest.fail(_command_diagnostic("dump corruption", corrupt_result), pytrace=False)

        restore_result = _command_result(
            [
                "docker",
                "exec",
                restore_context.container,
                "pg_restore",
                "--exit-on-error",
                "-U",
                "sentinel_admin",
                "-d",
                target_database,
                restore_context.dump_path,
            ]
        )
        if restore_result.exception_type is not None or restore_result.returncode == 0:
            pytest.fail(
                "Corrupt pg_restore did not fail as expected; error_type=unexpected-restore-result",
                pytrace=False,
            )
    finally:
        drop_error = _drop_database(restore_context.container, target_database)
        restore_context.extra_target_databases.discard(target_database)
        if drop_error is not None:
            pytest.fail(
                f"Corrupt restore target cleanup failed; error_type={drop_error}", pytrace=False
            )
        if await _database_exists(restore_context.source_connection, target_database):
            pytest.fail(
                "Corrupt restore target remains; error_type=database-not-dropped", pytrace=False
            )

    print("restore corrupt-dump: pg_restore_failed=true target_dropped=true")
