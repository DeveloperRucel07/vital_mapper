"""Passwort-Hashing mit dem Python-Standardalgorithmus scrypt (F-30)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from vital_mapper.application.ports.password_hasher_port import PasswordHasherPort

HASH_NAME = "scrypt"
SALT_BYTES = 16
DERIVED_KEY_BYTES = 32
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


class ScryptPasswordHasher(PasswordHasherPort):
    """Erzeugt versionierte, selbstbeschreibende scrypt-Passwort-Hashes."""

    def hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(SALT_BYTES)
        derived_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            dklen=DERIVED_KEY_BYTES,
        )
        return "$".join(
            (
                HASH_NAME,
                str(SCRYPT_N),
                str(SCRYPT_R),
                str(SCRYPT_P),
                _encode(salt),
                _encode(derived_key),
            )
        )

    def verify_password(self, password: str, encoded_hash: str) -> bool:
        try:
            algorithm, n, r, p, encoded_salt, encoded_key = encoded_hash.split("$")
            if algorithm != HASH_NAME:
                return False
            salt = _decode(encoded_salt)
            expected_key = _decode(encoded_key)
            if (
                len(salt) != SALT_BYTES
                or len(expected_key) != DERIVED_KEY_BYTES
                or int(n) != SCRYPT_N
                or int(r) != SCRYPT_R
                or int(p) != SCRYPT_P
            ):
                return False
            actual_key = hashlib.scrypt(
                password.encode("utf-8"),
                salt=salt,
                n=int(n),
                r=int(r),
                p=int(p),
                dklen=len(expected_key),
            )
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(actual_key, expected_key)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
