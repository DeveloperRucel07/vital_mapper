import uuid

from vital_mapper.infrastructure.security.audio_storage import EncryptedAudioStorage


async def test_audio_storage_encrypts_data_at_rest(tmp_path) -> None:
    storage = EncryptedAudioStorage(str(tmp_path))
    audio = b"synthetic audio bytes"
    reference = await storage.store(uuid.uuid4(), audio, "audio/webm")

    assert (tmp_path / reference).read_bytes() != audio
    assert await storage.load(reference) == audio


async def test_audio_storage_rejects_path_traversal(tmp_path) -> None:
    storage = EncryptedAudioStorage(str(tmp_path))

    try:
        await storage.load("..\\outside.enc")
    except ValueError:
        pass
    else:
        raise AssertionError("path traversal must be rejected")
