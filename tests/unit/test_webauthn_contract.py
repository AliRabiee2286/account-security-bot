import pytest

from app.modules.identity.webauthn_contract import (
    AssertionResult,
    WebAuthnNotConfigured,
    require_verified_assertion,
)


def test_unverified_assertion_fails_closed():
    with pytest.raises(WebAuthnNotConfigured):
        require_verified_assertion(AssertionResult(b"id", 1, False))


def test_verified_assertion_is_accepted():
    require_verified_assertion(AssertionResult(b"id", 1, True))
