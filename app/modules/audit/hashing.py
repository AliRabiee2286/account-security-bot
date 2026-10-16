"""S-015: tamper-evident hash chain over audit rows. Pure, testable."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical(record: dict[str, Any]) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), default=str).encode()


def chain_hash(prev_hash: str | None, record: dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update((prev_hash or "GENESIS").encode())
    h.update(canonical(record))
    return h.hexdigest()


def verify_chain(rows: list[tuple[dict[str, Any], str | None, str]]) -> int | None:
    """rows = [(record, prev_hash, row_hash)] in order. Return index of first broken row or None."""
    prev: str | None = None
    for i, (record, prev_hash, row_hash) in enumerate(rows):
        if prev_hash != prev or chain_hash(prev_hash, record) != row_hash:
            return i
        prev = row_hash
    return None
