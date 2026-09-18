import uuid
from datetime import UTC, datetime

from vital_mapper.application.ports.repository_port import RepositoryPort
from vital_mapper.domain.entities import Correction
from vital_mapper.domain.events import DomainEvent, EventType


class RecordCorrectionUseCase:
    """Speichert Korrekturen mit atomarer Outbox-Zustellung (UC-05/F-21/F-39)."""

    def __init__(self, repository: RepositoryPort) -> None:
        self._repository = repository

    async def execute(
        self,
        draft_id: uuid.UUID,
        field_path: str,
        prediction: str,
        correction: str,
        corrected_by: uuid.UUID,
    ) -> Correction:
        record = Correction(
            id=uuid.uuid4(),
            draft_id=draft_id,
            field_path=field_path,
            prediction=prediction,
            correction=correction,
            corrected_by=corrected_by,
            created_at=datetime.now(UTC),
        )
        event = DomainEvent(
            id=uuid.uuid4(),
            type=EventType.CORRECTION_RECORDED,
            occurred_at=datetime.now(UTC),
            payload={"correction_id": str(record.id), "field_path": field_path},
        )
        await self._repository.save_correction_and_enqueue_event(record, event)
        return record
