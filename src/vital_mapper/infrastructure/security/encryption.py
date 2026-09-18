from __future__ import annotations

from cryptography.fernet import Fernet

from vital_mapper.config import settings

_fernet = Fernet(settings.audio_encryption_key.encode())


def encrypt_bytes(data: bytes) -> bytes:
    return _fernet.encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    return _fernet.decrypt(token)
