from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from vital_mapper.config import settings

_fernet = Fernet(settings.audio_encryption_key.encode())
_clinical_fernet = Fernet(
    (settings.clinical_data_encryption_key or settings.audio_encryption_key).encode()
)
_clinical_decryptors = [_clinical_fernet]
if (
    settings.clinical_data_encryption_key
    and settings.clinical_data_encryption_key != settings.audio_encryption_key
):
    # Uebergangspfad fuer Entwicklungsdaten, die vor der Schluesseltrennung mit
    # dem Audio-Key verschluesselt wurden. Neue Schreibvorgaenge verwenden nur
    # den aktiven Clinical-Key.
    _clinical_decryptors.append(_fernet)
TRANSCRIPT_CIPHERTEXT_PREFIX = "fernet:v1:"


def encrypt_bytes(data: bytes) -> bytes:
    return _fernet.encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    return _fernet.decrypt(token)


def encrypt_transcript_text(text: str) -> str:
    """Verschluesselt ein Transkript mit versioniertem Speicherformat (F-26)."""

    token = _clinical_fernet.encrypt(text.encode("utf-8")).decode("ascii")
    return f"{TRANSCRIPT_CIPHERTEXT_PREFIX}{token}"


def decrypt_transcript_text(value: str) -> str:
    """Entschluesselt Transkripte und liest Altdaten bis zur Startmigration."""

    if not value.startswith(TRANSCRIPT_CIPHERTEXT_PREFIX):
        return value
    token = value.removeprefix(TRANSCRIPT_CIPHERTEXT_PREFIX)
    try:
        encoded_token = token.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("Transkript-Chiffrat ist ungueltig oder wurde manipuliert.") from exc
    for decryptor in _clinical_decryptors:
        try:
            return decryptor.decrypt(encoded_token).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError):
            continue
    raise ValueError("Transkript-Chiffrat ist ungueltig oder wurde manipuliert.")


def is_encrypted_transcript(value: str) -> bool:
    return value.startswith(TRANSCRIPT_CIPHERTEXT_PREFIX)
