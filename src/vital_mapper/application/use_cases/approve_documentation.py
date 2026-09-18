import uuid
from datetime import UTC, datetime

from vital_mapper.application.ports.repository_port import RepositoryPort
from vital_mapper.domain.entities import Approval, DraftStatus
from vital_mapper.domain.events import DomainEvent, EventType
from vital_mapper.domain.exceptions import (
    DraftAlreadyApprovedError,
    DraftNotEditableError,
)


class ApproveDocumentationUseCase:
    """Gibt einen Pflegebericht transaktional frei (UC-06/F-18/F-19)."""

    def __init__(self, repository: RepositoryPort) -> None:
        self._repository = repository

    async def execute(
        self, draft_id: uuid.UUID, approved_by: uuid.UUID, model_versions: dict[str, str]
    ) -> Approval:
        draft = await self._repository.get_draft(draft_id)

        if draft.status == DraftStatus.APPROVED:
            raise DraftAlreadyApprovedError(f"Draft {draft_id} wurde bereits freigegeben.")
        if draft.status == DraftStatus.DISCARDED:
            raise DraftNotEditableError(f"Draft {draft_id} wurde verworfen.")

        draft.status = DraftStatus.APPROVED
        draft.updated_at = datetime.now(UTC)

        approval = Approval(
            id=uuid.uuid4(),
            draft_id=draft_id,
            approved_by=approved_by,
            approved_at=datetime.now(UTC),
            model_versions=model_versions,
        )

        event = DomainEvent(
            id=uuid.uuid4(),
            type=EventType.DOCUMENTATION_APPROVED,
            occurred_at=datetime.now(UTC),
            payload={"draft_id": str(draft_id), "approved_by": str(approved_by)},
        )

        # Transaktionale Grenze: schlaegt einer der Schritte fehl, wird nichts
        # committet - siehe infrastructure/persistence/repository.py
        await self._repository.save_approval_and_enqueue_events(approval, draft, [event])

        return approval
