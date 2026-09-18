from __future__ import annotations

import httpx

from vital_mapper.application.ports.transcription_port import TranscriptionPort


class WhisperTranscriptionAdapter(TranscriptionPort):
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def transcribe(self, audio: bytes, language: str = "de") -> tuple[str, float, str]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=120.0) as client:
            response = await client.post(
                "/transcribe",
                files={"audio": ("recording.webm", audio, "audio/webm")},
                params={"language": language},
            )
            response.raise_for_status()
            data = response.json()
            return data["text"], data["confidence"], data["model_version"]
