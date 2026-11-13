"""Field-level encryption at rest: AES-256-GCM behind SQLAlchemy column types.

Stored layout: key id (1 byte) | nonce (12 bytes) | ciphertext + tag.
"""

import base64
import json
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import LargeBinary
from sqlalchemy.types import TypeDecorator

from app.config import get_settings


@lru_cache
def _keys() -> dict[int, AESGCM]:
    keys = {}
    for part in get_settings().data_encryption_keys.split(","):
        kid, _, b64 = part.strip().partition(":")
        raw = base64.b64decode(b64)
        if len(raw) != 32 or not 0 < int(kid) < 256:
            raise RuntimeError("DATA_ENCRYPTION_KEYS entries must be '<1-255>:<base64 32-byte key>'")
        keys[int(kid)] = AESGCM(raw)
    return keys


def encrypt(plain: bytes) -> bytes:
    kid = max(_keys())
    nonce = os.urandom(12)
    return bytes([kid]) + nonce + _keys()[kid].encrypt(nonce, plain, None)


def decrypt(blob: bytes) -> bytes:
    return _keys()[blob[0]].decrypt(blob[1:13], blob[13:], None)


class EncryptedBytes(TypeDecorator):
    """Binary column encrypted at rest. The audit log never records values of this type."""

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else encrypt(self._dump(value))

    def process_result_value(self, value, dialect):
        return None if value is None else self._load(decrypt(bytes(value)))

    def _dump(self, value) -> bytes:
        return value

    def _load(self, raw: bytes):
        return raw


class EncryptedText(EncryptedBytes):
    cache_ok = True

    def _dump(self, value) -> bytes:
        return value.encode()

    def _load(self, raw: bytes):
        return raw.decode()


class EncryptedJSON(EncryptedBytes):
    cache_ok = True

    def _dump(self, value) -> bytes:
        return json.dumps(value).encode()

    def _load(self, raw: bytes):
        return json.loads(raw)
