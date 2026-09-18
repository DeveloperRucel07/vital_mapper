from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vital_mapper.application.ports.repository_port import RepositoryPort
from vital_mapper.domain.entities import CareReportDraft, DraftStatus


class CreateCareReportDraftUseCase:
    """Erzeugt einen strikt transkriptgebundenen Berichtsentwurf (F-08/F-15)."""

    def __init__(self, repository: RepositoryPort) -> None:
        self._repository = repository

    async def execute(self, extraction_id: uuid.UUID) -> CareReportDraft:
        extraction = await self._repository.get_extraction(extraction_id)
        transcript = await self._repository.get_transcript(extraction.transcript_id)
        now = datetime.now(UTC)
        draft = CareReportDraft(
            id=uuid.uuid4(),
            extraction_id=extraction.id,
            report_text=transcript.text,
            status=DraftStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
        await self._repository.save_draft(draft)
        return draft
