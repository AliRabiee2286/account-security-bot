from app.adapters.social.oauth_policy import POLICIES, validate_scopes
from app.core.oauth import OAuthStart, pkce_pair, state_matches


def test_pkce_challenge_is_bound_to_verifier():
    verifier, challenge = pkce_pair()
    assert verifier and challenge and verifier != challenge


def test_state_is_hash_only_and_one_time_comparable():
    start, state, _challenge = OAuthStart.issue(provider="x", redirect_uri="https://app/callback")
    assert state_matches(state, start.state_hash)
    assert not state_matches("wrong", start.state_hash)
    assert state not in start.state_hash


def test_scopes_are_least_privilege():
    validate_scopes(POLICIES["x"], {"tweet.read", "users.read"})
    try:
        validate_scopes(POLICIES["x"], {"admin.read"})
        raise AssertionError("unexpected scope accepted")
    except ValueError:
        pass
