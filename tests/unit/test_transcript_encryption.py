import pytest

from vital_mapper.infrastructure.security.encryption import (
    TRANSCRIPT_CIPHERTEXT_PREFIX,
    decrypt_transcript_text,
    encrypt_transcript_text,
    is_encrypted_transcript,
)


def test_transcript_is_encrypted_at_rest() -> None:
    plaintext = "Synthetisches Transkript: Puls 76."

    ciphertext = encrypt_transcript_text(plaintext)

    assert ciphertext.startswith(TRANSCRIPT_CIPHERTEXT_PREFIX)
    assert plaintext not in ciphertext
    assert is_encrypted_transcript(ciphertext)
    assert decrypt_transcript_text(ciphertext) == plaintext


def test_legacy_plaintext_remains_readable_until_startup_migration() -> None:
    plaintext = "Synthetisches Altdaten-Transkript."

    assert not is_encrypted_transcript(plaintext)
    assert decrypt_transcript_text(plaintext) == plaintext


def test_manipulated_ciphertext_is_rejected() -> None:
    with pytest.raises(ValueError, match="ungueltig oder wurde manipuliert"):
        decrypt_transcript_text(f"{TRANSCRIPT_CIPHERTEXT_PREFIX}manipulated")
