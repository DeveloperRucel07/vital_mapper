from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from vital_mapper.application.ports.audio_storage_port import AudioStoragePort
from vital_mapper.infrastructure.security.encryption import decrypt_bytes, encrypt_bytes

_EXTENSIONS = {
    "audio/webm": ".webm",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
}


class EncryptedAudioStorage(AudioStoragePort):
    """Speichert Audiodaten verschluesselt und ohne Originaldateinamen (F-26/F-27)."""

    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    async def store(self, recording_id: uuid.UUID, audio: bytes, content_type: str) -> str:
        extension = _EXTENSIONS.get(content_type.lower())
        if extension is None:
            raise ValueError("Nicht unterstuetztes Audioformat.")
        path = self._root / f"{recording_id.hex}{extension}.enc"
        await asyncio.to_thread(path.write_bytes, encrypt_bytes(audio))
        return path.name

    async def load(self, audio_ref: str) -> bytes:
        path = self._safe_path(audio_ref)
        return decrypt_bytes(await asyncio.to_thread(path.read_bytes))

    async def delete(self, audio_ref: str) -> None:
        path = self._safe_path(audio_ref)
        await asyncio.to_thread(path.unlink, missing_ok=True)

    def _safe_path(self, audio_ref: str) -> Path:
        candidate = (self._root / audio_ref).resolve()
        if candidate.parent != self._root or candidate.name != audio_ref:
            raise ValueError("Ungueltige Audio-Referenz.")
        return candidate
