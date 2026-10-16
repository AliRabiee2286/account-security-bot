"""S-004 / S-016: envelope encryption behind a KeyProvider interface.

- Each data group (e.g. department) has its own Data Encryption Key (DEK).
- DEKs are stored wrapped by the master Key Encryption Key (KEK) held by the KeyProvider.
- The KEK never lives in the database or on the DB host.
- AES-256-GCM with Associated Data binding ciphertext to (owner_type, owner_id, key_version),
  so a ciphertext copied onto another row fails to decrypt.
"""

from __future__ import annotations

import base64
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_LEN = 12
KEY_LEN = 32


class KeyProvider(Protocol):
    """Swappable: LocalKeyProvider now, Vault/KMS adapter later (adapters/keys)."""

    def wrap(self, dek: bytes, *, context: bytes) -> bytes: ...
    def unwrap(self, wrapped: bytes, *, context: bytes) -> bytes: ...
    @property
    def kek_version(self) -> int: ...


class LocalKeyProvider:
    def __init__(self, kek: bytes, version: int = 1) -> None:
        if len(kek) != KEY_LEN:
            raise ValueError("KEK must be 32 bytes")
        self._aead = AESGCM(kek)
        self._version = version

    @classmethod
    def from_file(cls, path: str | Path, version: int = 1) -> LocalKeyProvider:
        raw = Path(path).read_text(encoding="ascii").strip()
        return cls(base64.b64decode(raw), version)

    @property
    def kek_version(self) -> int:
        return self._version

    def wrap(self, dek: bytes, *, context: bytes) -> bytes:
        nonce = os.urandom(NONCE_LEN)
        return nonce + self._aead.encrypt(nonce, dek, context)

    def unwrap(self, wrapped: bytes, *, context: bytes) -> bytes:
        return self._aead.decrypt(wrapped[:NONCE_LEN], wrapped[NONCE_LEN:], context)


@dataclass(frozen=True)
class Sealed:
    ciphertext: bytes  # nonce || ct || tag
    key_version: int


def _aad(owner_type: str, owner_id: str, key_version: int) -> bytes:
    return f"{owner_type}|{owner_id}|v{key_version}".encode()


def new_dek() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def seal(
    dek: bytes, plaintext: bytes, *, owner_type: str, owner_id: str, key_version: int
) -> Sealed:
    nonce = os.urandom(NONCE_LEN)
    ct = AESGCM(dek).encrypt(nonce, plaintext, _aad(owner_type, owner_id, key_version))
    return Sealed(nonce + ct, key_version)


def open_sealed(dek: bytes, sealed: Sealed, *, owner_type: str, owner_id: str) -> bytes:
    aad = _aad(owner_type, owner_id, sealed.key_version)
    return AESGCM(dek).decrypt(sealed.ciphertext[:NONCE_LEN], sealed.ciphertext[NONCE_LEN:], aad)


def generate_master_key_b64() -> str:
    return base64.b64encode(os.urandom(KEY_LEN)).decode("ascii")


if __name__ == "__main__" and sys.argv[1:] == ["gen-key"]:
    print(generate_master_key_b64())
