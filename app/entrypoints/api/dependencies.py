from __future__ import annotations

from fastapi import Depends

from app.core.auth_context import AuthContext
from app.core.auth_resolver import resolve_auth_context


async def current_auth(
    ctx: AuthContext = Depends(resolve_auth_context),  # noqa: B008 - FastAPI dependency injection
) -> AuthContext:
    return ctx
