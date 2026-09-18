from __future__ import annotations

import uuid

from vital_mapper.application.ports.repository_port import RepositoryPort
from vital_mapper.domain.entities import ExtractionResult
from vital_mapper.domain.value_objects import ClinicalExtraction


class UpdateClinicalExtractionUseCase:
    """Speichert eine manuelle Korrektur der strukturierten Extraktion (F-13)."""

    def __init__(self, repository: RepositoryPort) -> None:
        self._repository = repository

    async def execute(self, extraction_id: uuid.UUID, data: ClinicalExtraction) -> ExtractionResult:
        return await self._repository.update_extraction_data(extraction_id, data)
