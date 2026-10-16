import pytest
from cryptography.exceptions import InvalidTag

from app.core.crypto import LocalKeyProvider, new_dek, open_sealed, seal


def test_envelope_round_trip_and_context_binding():
    provider = LocalKeyProvider(b"k" * 32, version=7)
    dek = new_dek()
    wrapped = provider.wrap(dek, context=b"social_account:account-1")
    unwrapped = provider.unwrap(wrapped, context=b"social_account:account-1")
    sealed = seal(
        unwrapped, b"secret-value", owner_type="social_account", owner_id="account-1", key_version=7
    )
    assert (
        open_sealed(unwrapped, sealed, owner_type="social_account", owner_id="account-1")
        == b"secret-value"
    )
    with pytest.raises(InvalidTag):
        provider.unwrap(wrapped, context=b"social_account:account-2")
    with pytest.raises(InvalidTag):
        open_sealed(unwrapped, sealed, owner_type="social_account", owner_id="account-2")
