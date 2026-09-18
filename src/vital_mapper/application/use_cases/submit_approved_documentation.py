from __future__ import annotations

import uuid
from typing import Any

from vital_mapper.application.ports.nursing_report_port import NursingReportPort
from vital_mapper.application.ports.repository_port import RepositoryPort


class SubmitApprovedDocumentationUseCase:
    """Uebergibt einen freigegebenen Bericht an den Monitoring-Gateway (F-20/F-23)."""

    def __init__(self, repository: RepositoryPort, gateway: NursingReportPort) -> None:
        self._repository = repository
        self._gateway = gateway

    async def execute(self, draft_id: uuid.UUID, access_token: str) -> dict[str, Any]:
        documentation = await self._repository.get_approved_documentation(draft_id)
        return await self._gateway.submit_nursing_report(
            documentation.patient_ref,
            documentation.report_text,
            documentation.extraction,
            documentation.recorded_at,
            access_token,
        )
