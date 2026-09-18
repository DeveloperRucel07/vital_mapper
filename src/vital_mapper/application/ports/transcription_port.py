from abc import ABC, abstractmethod


class TranscriptionPort(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, language: str = "de") -> tuple[str, float, str]:
        """Gibt (Text, Konfidenz, Modellversion) zurueck."""
