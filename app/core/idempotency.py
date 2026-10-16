"""Idempotency keys for retries and user double-submit protection."""

from __future__ import annotations

import hashlib


def key(*parts: str) -> str:
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
