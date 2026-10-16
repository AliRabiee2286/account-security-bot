"""Provider OAuth policy: least scopes and exact redirect/issuer allowlists."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OAuthPolicy:
    provider: str
    issuer: str
    allowed_scopes: frozenset[str]
    redirect_uri: str


POLICIES = {
    "x": OAuthPolicy(
        "x",
        "https://twitter.com",
        frozenset({"tweet.read", "tweet.write", "users.read", "offline.access"}),
        "",
    ),
    "instagram": OAuthPolicy(
        "instagram",
        "https://www.facebook.com",
        frozenset({"instagram_business_basic", "instagram_business_manage_comments"}),
        "",
    ),
}


def validate_scopes(policy: OAuthPolicy, requested: set[str]) -> None:
    if not requested or not requested <= policy.allowed_scopes:
        raise ValueError("requested OAuth scope is not allowed")
