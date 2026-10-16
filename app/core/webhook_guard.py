"""S-005: reject any webhook call without the exact Telegram secret token (constant-time)."""

from __future__ import annotations

import hmac

HEADER = "X-Telegram-Bot-Api-Secret-Token"
MIN_SECRET_LEN = 32


def validate_secret_config(secret: str) -> None:
    if len(secret) < MIN_SECRET_LEN or not all(c.isalnum() or c in "_-" for c in secret):
        raise ValueError("TELEGRAM_WEBHOOK_SECRET must be >=32 chars of [A-Za-z0-9_-]")


def is_valid_webhook(received: str | None, expected: str) -> bool:
    if not received or not expected:
        return False
    return hmac.compare_digest(received.encode(), expected.encode())
