from datetime import timedelta
from uuid import uuid4

from app.core.one_time_form import FormClaims, token_matches, validate_token_shape
from app.core.redaction import redact
from app.core.webhook_guard import is_valid_webhook
from app.modules.audit.hashing import chain_hash, verify_chain


def test_form_is_one_shot_shape_and_hash_only():
    claims, raw = FormClaims.issue(subject_id=str(uuid4()), purpose="credential_entry")
    assert validate_token_shape(raw)
    assert token_matches(raw, claims.token_hash)
    assert raw not in claims.token_hash
    assert not claims.is_expired()


def test_form_expiry():
    claims, _ = FormClaims.issue(subject_id="x", purpose="social_oauth", ttl=timedelta(seconds=-1))
    assert claims.is_expired()


def test_webhook_constant_time_guard():
    assert is_valid_webhook("a" * 32, "a" * 32)
    assert not is_valid_webhook("a" * 31, "a" * 32)
    assert not is_valid_webhook(None, "a" * 32)


def test_redaction_nested_and_jwt():
    out = redact({"password": "x", "nested": {"token": "y"}, "text": "Bearer abc.def"})
    assert out["password"] == "***"  # noqa: S105 - redaction fixture key
    assert out["nested"]["token"] == "***"  # noqa: S105 - redaction fixture key
    assert out["text"] == "***"


def test_hash_chain_detects_tampering():
    a, b = {"action": "a"}, {"action": "b"}
    ha, hb = chain_hash(None, a), chain_hash(chain_hash(None, a), b)
    assert verify_chain([(a, None, ha), (b, ha, hb)]) is None
    assert verify_chain([({"action": "tampered"}, None, ha), (b, ha, hb)]) == 0
