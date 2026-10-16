"""Shared token digests preserve session/form compatibility and constant-time matching."""

from __future__ import annotations

import hmac
from unittest.mock import patch

from app.core.one_time_form import FormClaims, token_matches
from app.core.session import issue_session, verify_session
from app.core.token_hash import hash_token, matches_token


def test_hash_token_is_deterministic_sha256() -> None:
    expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert hash_token("abc") == expected
    assert hash_token("abc") == hash_token("abc")
    assert "abc" not in hash_token("abc")


def test_matches_token_uses_constant_time_comparison() -> None:
    raw = "dummy-session-secret"
    digest = hash_token(raw)
    with patch("app.core.token_hash.hmac.compare_digest", wraps=hmac.compare_digest) as compare:
        assert matches_token(raw, digest)
        assert not matches_token("wrong-token", digest)

    assert compare.call_count == 2
    assert compare.call_args_list[0].args == (digest, digest)
    assert compare.call_args_list[1].args == (hash_token("wrong-token"), digest)


def test_session_and_form_use_shared_digest_without_retaining_raw_tokens() -> None:
    raw, digest = issue_session()
    assert digest == hash_token(raw)
    assert raw not in digest
    assert verify_session(raw, digest)
    assert not verify_session("wrong-token", digest)

    claims, form_token = FormClaims.issue(subject_id="subject", purpose="credential_entry")
    assert claims.token_hash == hash_token(form_token)
    assert form_token not in repr(claims)
    assert token_matches(form_token, claims.token_hash)
    assert not token_matches("wrong-token", claims.token_hash)
