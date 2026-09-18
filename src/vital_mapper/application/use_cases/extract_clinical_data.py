import uuid
from datetime import UTC, datetime

from vital_mapper.application.ports.event_bus_port import EventBusPort
from vital_mapper.application.ports.extraction_port import ExtractionPort
from vital_mapper.application.ports.repository_port import RepositoryPort
from vital_mapper.domain.entities import ExtractionResult
from vital_mapper.domain.events import DomainEvent, EventType


class ExtractClinicalDataUseCase:
    def __init__(
        self,
        extraction: ExtractionPort,
        repository: RepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._extraction = extraction
        self._repository = repository
        self._event_bus = event_bus

    async def execute(
        self, transcript_id: uuid.UUID, transcript_text: str | None = None
    ) -> ExtractionResult:
        if transcript_text is None:
            transcript_text = (await self._repository.get_transcript(transcript_id)).text
        else:
            await self._repository.update_transcript_text(transcript_id, transcript_text)
        data, model_version = await self._extraction.extract(transcript_text)

        result = ExtractionResult(
            id=uuid.uuid4(),
            transcript_id=transcript_id,
            data=data,
            ollama_version=model_version,
            created_at=datetime.now(UTC),
        )
        await self._repository.save_extraction(result)

        await self._event_bus.publish(
            DomainEvent(
                id=uuid.uuid4(),
                type=EventType.EXTRACTION_COMPLETED,
                occurred_at=datetime.now(UTC),
                payload={
                    "extraction_id": str(result.id),
                    "unsichere_felder": data.unsichere_felder,
                },
            )
        )
        return result
