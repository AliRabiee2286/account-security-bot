"""Shared egress policy for all external adapters (S-020)."""

from __future__ import annotations

from urllib.parse import urlparse

ALLOWED_SCHEMES = {"https"}


class EgressPolicyError(ValueError):
    pass


def validate_endpoint(url: str, allowed_hosts: frozenset[str]) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.hostname:
        raise EgressPolicyError("only https endpoint URLs are allowed")
    host = parsed.hostname.lower().rstrip(".")
    if host not in allowed_hosts:
        raise EgressPolicyError("endpoint host is not allowlisted")
    if parsed.username or parsed.password:
        raise EgressPolicyError("userinfo in endpoint is forbidden")
