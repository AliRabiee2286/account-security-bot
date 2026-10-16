"""S-010: central redaction. Every log record and audit metadata passes through here.

Pure module (stdlib only) so it can be unit-tested and reused by any sink.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

MASK = "***"
_SENSITIVE_KEY = re.compile(
    r"(pass(word)?|pwd|secret|token|seed|mnemonic|api[_-]?key|authorization|cookie|"
    r"private[_-]?key|otp|code_verifier|ciphertext)",
    re.IGNORECASE,
)
# Values that look like secrets even under innocent keys.
_SENSITIVE_VALUE = [
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),  # Telegram bot token
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+=*", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),  # JWT
]
_MAX_DEPTH = 8


def is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY.search(key))


def redact_str(value: str) -> str:
    for pattern in _SENSITIVE_VALUE:
        value = pattern.sub(MASK, value)
    return value


def redact(value: Any, _depth: int = 0) -> Any:
    """Return a deep copy of ``value`` with sensitive keys and secret-looking strings masked."""
    if _depth > _MAX_DEPTH:
        return MASK
    if isinstance(value, Mapping):
        return {
            k: (MASK if isinstance(k, str) and is_sensitive_key(k) else redact(v, _depth + 1))
            for k, v in value.items()
        }
    if isinstance(value, list | tuple | set):
        return type(value)(redact(v, _depth + 1) for v in value)
    if isinstance(value, str):
        return redact_str(value)
    return value
