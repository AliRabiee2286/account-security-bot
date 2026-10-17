"""Guard Alembic migrations against asyncpg-incompatible multi-statement executes."""

from __future__ import annotations

import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_DIR = PROJECT_ROOT / "migrations" / "versions"
DOLLAR_TAG = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$")


def _static_sql(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                parts.append("__EXPR__")
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _static_sql(node.left) + _static_sql(node.right)
    raise AssertionError(f"unsupported op.execute argument at line {node.lineno}")


def _split_sql(sql: str) -> list[str]:  # noqa: PLR0912 - SQL lexer states are explicit
    statements: list[str] = []
    start = 0
    index = 0
    quote: str | None = None
    dollar_tag: str | None = None
    while index < len(sql):
        if dollar_tag is not None:
            if sql.startswith(dollar_tag, index):
                index += len(dollar_tag)
                dollar_tag = None
            else:
                index += 1
            continue

        char = sql[index]
        if quote is not None:
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    index += 2
                    continue
                quote = None
            elif char == "\\" and quote == "'":
                index += 2
                continue
            index += 1
            continue

        if char in ("'", '"'):
            quote = char
            index += 1
            continue
        if char == "$":
            match = DOLLAR_TAG.match(sql, index)
            if match is not None:
                dollar_tag = match.group(0)
                index = match.end()
                continue
        if char == ";":
            statement = sql[start:index].strip()
            if statement:
                statements.append(statement)
            start = index + 1
        index += 1

    statement = sql[start:].strip()
    if statement:
        statements.append(statement)
    return statements


def test_split_sql_detects_two_statements() -> None:
    sql = "CREATE TABLE first_table (id integer); CREATE TABLE second_table (id integer);"

    assert _split_sql(sql) == [
        "CREATE TABLE first_table (id integer)",
        "CREATE TABLE second_table (id integer)",
    ]


def test_split_sql_keeps_semicolons_inside_dollar_quote_in_one_statement() -> None:
    sql = """
    CREATE FUNCTION audit.example() RETURNS void AS $$
    BEGIN
        PERFORM 1;
        RAISE NOTICE 'inside body; still one statement';
    END $$ LANGUAGE plpgsql;
    """

    assert len(_split_sql(sql)) == 1


def test_split_sql_keeps_semicolons_inside_single_quotes_in_one_statement() -> None:
    assert _split_sql("SELECT 'inside; quote';") == ["SELECT 'inside; quote'"]


def test_migrations_use_one_sql_statement_per_op_execute() -> None:
    violations: list[str] = []
    for path in sorted(MIGRATION_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "execute"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "op"
        ]
        for call in sorted(calls, key=lambda node: (node.lineno, node.col_offset)):
            sql = _static_sql(call.args[0])
            statement_count = len(_split_sql(sql))
            if statement_count != 1:
                violations.append(f"{path}:{call.lineno}: {statement_count} SQL statements")

    assert not violations, "\n".join(violations)
