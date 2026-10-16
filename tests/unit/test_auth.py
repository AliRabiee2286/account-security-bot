from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.mfa import require_privileged_mfa
from app.core.session import SessionClaims, issue_session, verify_session


def test_session_is_hash_only_and_verifiable():
    raw, stored = issue_session()
    assert raw not in stored and verify_session(raw, stored)
    assert not verify_session("wrong", stored)


def test_privileged_requires_webauthn():
    assert not require_privileged_mfa({"telegram"}).satisfied
    assert require_privileged_mfa({"telegram", "webauthn"}).satisfied


def test_session_expiry():
    c = SessionClaims(
        uuid4(), uuid4(), "h", datetime.now(UTC) - timedelta(seconds=1), ("webauthn",)
    )
    assert not c.active()
