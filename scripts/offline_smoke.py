"""Executable offline smoke checks for security primitives (no DB/network required)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.crypto import LocalKeyProvider, new_dek, open_sealed, seal
from app.core.one_time_form import FormClaims, token_matches, validate_token_shape
from app.core.session import issue_session, verify_session
from app.core.webhook_guard import is_valid_webhook

provider = LocalKeyProvider(b"K" * 32, version=3)
dek = new_dek()
wrapped = provider.wrap(dek, context=b"owner:1")
if provider.unwrap(wrapped, context=b"owner:1") != dek:
    raise SystemExit("envelope key wrapping round trip failed")
sealed = seal(dek, b"secret", owner_type="social_account", owner_id="1", key_version=3)
if open_sealed(dek, sealed, owner_type="social_account", owner_id="1") != b"secret":
    raise SystemExit("envelope sealing round trip failed")
failed_closed = False
try:
    open_sealed(dek, sealed, owner_type="social_account", owner_id="2")
except Exception:
    failed_closed = True
if not failed_closed:
    raise SystemExit("AAD binding failed")
claims, token = FormClaims.issue(subject_id="subject", purpose="credential_entry")
if not validate_token_shape(token) or not token_matches(token, claims.token_hash):
    raise SystemExit("one-time token validation failed")
raw, token_hash = issue_session()
if not verify_session(raw, token_hash):
    raise SystemExit("session hash verification failed")
if not is_valid_webhook("a" * 32, "a" * 32) or is_valid_webhook("x" * 32, "a" * 32):
    raise SystemExit("webhook secret guard failed")
print(
    "offline smoke: envelope encryption, AAD binding, one-time token, session hash, "
    "webhook guard: PASS"
)
