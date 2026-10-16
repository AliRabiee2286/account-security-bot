import pytest

from app.modules.identity.webauthn_policy import WebAuthnPolicy


def test_privileged_webauthn_policy_requires_https_and_uv():
    WebAuthnPolicy("bot.example.com", "https://bot.example.com").validate()
    with pytest.raises(ValueError):
        WebAuthnPolicy("bot.example.com", "http://bot.example.com").validate()
    with pytest.raises(ValueError):
        WebAuthnPolicy(
            "bot.example.com", "https://bot.example.com", user_verification="preferred"
        ).validate()
