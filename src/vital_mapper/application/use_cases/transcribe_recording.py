import uuid
from datetime import UTC, datetime

from vital_mapper.application.ports.audio_storage_port import AudioStoragePort
from vital_mapper.application.ports.event_bus_port import EventBusPort
from vital_mapper.application.ports.repository_port import RepositoryPort
from vital_mapper.application.ports.transcription_port import TranscriptionPort
from vital_mapper.domain.entities import Transcript
from vital_mapper.domain.events import DomainEvent, EventType


class TranscribeRecordingUseCase:
    def __init__(
        self,
        transcription: TranscriptionPort,
        repository: RepositoryPort,
        audio_storage: AudioStoragePort,
        event_bus: EventBusPort,
    ) -> None:
        self._transcription = transcription
        self._repository = repository
        self._audio_storage = audio_storage
        self._event_bus = event_bus

    async def execute(self, recording_id: uuid.UUID) -> Transcript:
        recording = await self._repository.get_recording(recording_id)
        audio = await self._audio_storage.load(recording.audio_ref)
        text, confidence, model_version = await self._transcription.transcribe(audio)

        transcript = Transcript(
            id=uuid.uuid4(),
            recording_id=recording_id,
            text=text,
            confidence=confidence,
            whisper_version=model_version,
            created_at=datetime.now(UTC),
        )
        await self._repository.save_transcript(transcript)

        await self._event_bus.publish(
            DomainEvent(
                id=uuid.uuid4(),
                type=EventType.TRANSCRIPT_READY,
                occurred_at=datetime.now(UTC),
                payload={"transcript_id": str(transcript.id), "recording_id": str(recording_id)},
            )
        )
        return transcript
