import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from vital_mapper.application.use_cases.submit_approved_documentation import (
    SubmitApprovedDocumentationUseCase,
)
from vital_mapper.domain.entities import ApprovedDocumentation
from vital_mapper.domain.value_objects import ClinicalExtraction


class FakeRepository:
    async def get_approved_documentation(self, draft_id: uuid.UUID) -> ApprovedDocumentation:
        return ApprovedDocumentation(
            patient_ref="synthetic-patient-1",
            report_text="Synthetischer Pflegebericht.",
            extraction=ClinicalExtraction(),
            recorded_at=datetime.now(UTC),
        )


class FakeGateway:
    def __init__(self) -> None:
        self.call: tuple[str, str, ClinicalExtraction, datetime, str] | None = None

    async def submit_nursing_report(
        self,
        patient_ref: str,
        report_text: str,
        extraction: ClinicalExtraction,
        recorded_at: datetime,
        access_token: str,
    ) -> dict[str, Any]:
        self.call = (patient_ref, report_text, extraction, recorded_at, access_token)
        return {"resourceType": "Composition", "id": "synthetic-report-1"}


@pytest.mark.asyncio
async def test_approved_documentation_is_forwarded_to_monitoring_gateway() -> None:
    gateway = FakeGateway()
    draft_id = uuid.uuid4()

    result = await SubmitApprovedDocumentationUseCase(FakeRepository(), gateway).execute(
        draft_id, "synthetic-access-token"
    )

    assert result["id"] == "synthetic-report-1"
    assert gateway.call is not None
    assert gateway.call[0] == "synthetic-patient-1"
    assert gateway.call[1] == "Synthetischer Pflegebericht."
    assert isinstance(gateway.call[2], ClinicalExtraction)
    assert gateway.call[3].tzinfo is not None
    assert gateway.call[4] == "synthetic-access-token"
