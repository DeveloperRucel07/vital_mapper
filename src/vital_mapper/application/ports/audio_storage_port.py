from __future__ import annotations

import uuid
from abc import ABC, abstractmethod


class AudioStoragePort(ABC):
    """Port für verschlüsselte Audiodaten (F-26/F-27)."""

    @abstractmethod
    async def store(self, recording_id: uuid.UUID, audio: bytes, content_type: str) -> str: ...

    @abstractmethod
    async def load(self, audio_ref: str) -> bytes: ...

    @abstractmethod
    async def delete(self, audio_ref: str) -> None: ...
