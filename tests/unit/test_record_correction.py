import uuid

from vital_mapper.application.use_cases.record_correction import RecordCorrectionUseCase
from vital_mapper.domain.entities import Correction
from vital_mapper.domain.events import DomainEvent, EventType


class FakeRepository:
    def __init__(self) -> None:
        self.correction: Correction | None = None
        self.event: DomainEvent | None = None

    async def save_correction_and_enqueue_event(
        self, correction: Correction, event: DomainEvent
    ) -> None:
        self.correction = correction
        self.event = event


async def test_correction_and_event_are_written_together() -> None:
    repository = FakeRepository()
    use_case = RecordCorrectionUseCase(repository)  # type: ignore[arg-type]
    draft_id = uuid.uuid4()

    correction = await use_case.execute(
        draft_id=draft_id,
        field_path="vitalparameter.puls",
        prediction="76",
        correction="78",
        corrected_by=uuid.uuid4(),
    )

    assert repository.correction == correction
    assert repository.event is not None
    assert repository.event.type == EventType.CORRECTION_RECORDED
    assert repository.event.payload["correction_id"] == str(correction.id)
