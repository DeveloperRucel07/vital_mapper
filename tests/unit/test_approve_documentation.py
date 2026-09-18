import uuid
from datetime import UTC, datetime

import pytest

from vital_mapper.application.use_cases.approve_documentation import (
    ApproveDocumentationUseCase,
)
from vital_mapper.domain.entities import CareReportDraft, DraftStatus
from vital_mapper.domain.exceptions import DraftAlreadyApprovedError


class FakeRepository:
    def __init__(self, draft: CareReportDraft) -> None:
        self._draft = draft
        self.saved = False

    async def get_draft(self, draft_id: uuid.UUID) -> CareReportDraft:
        return self._draft

    async def save_approval_and_enqueue_events(self, approval, draft, events) -> None:
        self.saved = True


async def test_cannot_approve_twice() -> None:
    draft = CareReportDraft(
        id=uuid.uuid4(),
        extraction_id=uuid.uuid4(),
        report_text="...",
        status=DraftStatus.APPROVED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    repo = FakeRepository(draft)
    use_case = ApproveDocumentationUseCase(repo)

    with pytest.raises(DraftAlreadyApprovedError):
        await use_case.execute(draft.id, uuid.uuid4(), {"ollama": "llama3.1"})

    assert repo.saved is False
