"""FastAPI session resolver: bearer/cookie token -> DB session -> AuthContext.

This is intentionally database-backed and fail-closed. Telegram identity proof is performed
at session issuance, never inferred from a client-supplied employee ID.
"""

from __future__ import annotations

from fastapi import Cookie, Header, HTTPException
from sqlalchemy import text

from app.core.auth_context import AuthContext
from app.core.db import unit_of_work
from app.core.token_hash import hash_token

MAX_TOKEN_LENGTH = 512


async def resolve_auth_context(
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(default=None, alias="sentinel_session"),
) -> AuthContext:
    raw = session_cookie
    if authorization and authorization.startswith("Bearer "):
        raw = authorization[7:].strip()
    if not raw or len(raw) > MAX_TOKEN_LENGTH:
        raise HTTPException(status_code=401, detail="authentication required")
    async with unit_of_work() as db:
        result = await db.execute(
            text("""
          SELECT s.id, s.employee_id, s.token_hash, s.expires_at, s.amr
            FROM identity.sessions s JOIN identity.employees e ON e.id=s.employee_id
           WHERE s.token_hash = :token_hash AND s.revoked_at IS NULL
             AND s.expires_at > now() AND e.status = 'active'
        """),
            {"token_hash": hash_token(raw)},
        )
        match = result.mappings().first()
        if match is None:
            raise HTTPException(status_code=401, detail="invalid or expired session")
        methods = tuple(filter(None, str(match["amr"]).split(",")))
        return AuthContext(employee_id=match["employee_id"], session_id=match["id"], amr=methods)
