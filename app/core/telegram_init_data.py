"""Telegram Mini App initData validation.

Reference: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
The client-supplied user object is accepted only after HMAC validation and freshness checks.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


@dataclass(frozen=True)
class TelegramIdentity:
    user_id: int
    first_name: str
    username: str | None
    auth_date: int
    query_id: str | None


class InvalidInitData(ValueError):
    pass


MAX_INIT_DATA_LENGTH = 8192
SHA256_HEX_LENGTH = 64


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()


def validate_init_data(
    init_data: str, *, bot_token: str, max_age_seconds: int = 300, now: int | None = None
) -> TelegramIdentity:
    if not init_data or len(init_data) > MAX_INIT_DATA_LENGTH:
        raise InvalidInitData("missing or oversized initData")
    parsed = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    if len({key for key, _ in parsed}) != len(parsed):
        raise InvalidInitData("duplicate field")
    pairs = dict(parsed)
    received_hash = pairs.pop("hash", "")
    if not received_hash or len(received_hash) != SHA256_HEX_LENGTH:
        raise InvalidInitData("missing hash")
    data_check = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    expected = hmac.new(
        _secret_key(bot_token), data_check.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InvalidInitData("invalid signature")
    try:
        auth_date = int(pairs["auth_date"])
        user = json.loads(pairs["user"])
        user_id = int(user["id"])
        first_name = str(user.get("first_name", "")).strip()
        last_name = str(user.get("last_name", "")).strip()
        full_name = " ".join(part for part in (first_name, last_name) if part)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InvalidInitData("invalid identity payload") from exc
    timestamp = int(time.time()) if now is None else now
    if auth_date > timestamp + 30 or timestamp - auth_date > max_age_seconds:
        raise InvalidInitData("stale identity proof")
    if not full_name or user_id <= 0:
        raise InvalidInitData("incomplete identity payload")
    return TelegramIdentity(
        user_id, full_name, user.get("username"), auth_date, pairs.get("query_id")
    )
