"""Authentication boundary: no endpoint trusts actor IDs from request data."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.mfa import require_privileged_mfa


@dataclass(frozen=True)
class AuthContext:
    employee_id: UUID
    session_id: UUID
    amr: tuple[str, ...]
    privileged: bool = False


class AuthenticationUnavailable(RuntimeError):
    pass


async def require_authentication() -> AuthContext:
    raise AuthenticationUnavailable("authentication provider is not configured")


def require_privileged(ctx: AuthContext) -> None:
    if not ctx.privileged or not require_privileged_mfa(set(ctx.amr)).satisfied:
        raise PermissionError("phishing-resistant MFA required")
