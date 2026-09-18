from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vital_mapper.application.ports.repository_port import RepositoryPort
from vital_mapper.domain.entities import CareReportDraft, DraftStatus
from vital_mapper.domain.exceptions import DraftAlreadyApprovedError, DraftNotEditableError


class UpdateCareReportDraftUseCase:
    """Speichert die fachliche Pruefung eines Entwurfs (UC-05/UC-06)."""

    def __init__(self, repository: RepositoryPort) -> None:
        self._repository = repository

    async def execute(self, draft_id: uuid.UUID, report_text: str) -> CareReportDraft:
        draft = await self._repository.get_draft(draft_id)
        if draft.status == DraftStatus.APPROVED:
            raise DraftAlreadyApprovedError("Ein freigegebener Entwurf ist unveraenderlich.")
        if draft.status == DraftStatus.DISCARDED:
            raise DraftNotEditableError("Ein verworfener Entwurf ist nicht editierbar.")
        if not report_text.strip():
            raise ValueError("Der Bericht darf nicht leer sein.")
        draft.report_text = report_text
        draft.updated_at = datetime.now(UTC)
        return await self._repository.update_draft_text(draft_id, report_text)
