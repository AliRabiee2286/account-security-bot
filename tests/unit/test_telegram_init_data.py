import hashlib
import hmac
import json

import pytest

from app.core.telegram_init_data import InvalidInitData, validate_init_data


def signed(bot_token: str, auth_date: int = 1_700_000_000) -> str:
    fields = {
        "auth_date": str(auth_date),
        "query_id": "q1",
        "user": json.dumps({"id": 123, "first_name": "A"}, separators=(",", ":")),
    }
    check = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return "&".join(f"{k}={v}" for k, v in fields.items()) + "&hash=" + digest


def test_valid_signed_init_data():
    dummy_token = "123:ABC"  # noqa: S105 - test-only dummy token
    identity = validate_init_data(signed(dummy_token), bot_token=dummy_token, now=1_700_000_100)
    assert identity.user_id == 123


def test_tampering_and_stale_data_fail():
    dummy_token = "123:ABC"  # noqa: S105 - test-only dummy token
    raw = signed(dummy_token)
    with pytest.raises(InvalidInitData):
        validate_init_data(
            raw[:-1] + ("0" if raw[-1] != "0" else "1"),
            bot_token=dummy_token,
            now=1_700_000_100,
        )
    with pytest.raises(InvalidInitData):
        validate_init_data(raw, bot_token=dummy_token, now=1_700_001_000)
