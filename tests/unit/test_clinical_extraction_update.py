import uuid
from datetime import UTC, datetime

import pytest

from vital_mapper.application.use_cases.update_clinical_extraction import (
    UpdateClinicalExtractionUseCase,
)
from vital_mapper.domain.entities import ExtractionResult
from vital_mapper.domain.value_objects import ClinicalExtraction, Vitalparameter


class FakeRepository:
    def __init__(self) -> None:
        self.updated: tuple[uuid.UUID, ClinicalExtraction] | None = None

    async def update_extraction_data(
        self, extraction_id: uuid.UUID, data: ClinicalExtraction
    ) -> ExtractionResult:
        self.updated = (extraction_id, data)
        return ExtractionResult(
            id=extraction_id,
            transcript_id=uuid.uuid4(),
            data=data,
            ollama_version="llama3.2:latest",
            created_at=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_manual_json_correction_is_forwarded_to_repository() -> None:
    repository = FakeRepository()
    extraction_id = uuid.uuid4()
    data = ClinicalExtraction(vitalparameter=Vitalparameter(puls=85))

    result = await UpdateClinicalExtractionUseCase(repository).execute(extraction_id, data)

    assert repository.updated == (extraction_id, data)
    assert result.data.vitalparameter is not None
    assert result.data.vitalparameter.puls == 85
