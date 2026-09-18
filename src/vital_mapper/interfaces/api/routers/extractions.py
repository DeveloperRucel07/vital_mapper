"""Manuelle Korrektur strukturierter klinischer Extraktionen (F-13)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from vital_mapper.application.use_cases.update_clinical_extraction import (
    UpdateClinicalExtractionUseCase,
)
from vital_mapper.domain.entities import UserRole
from vital_mapper.domain.exceptions import AccessDeniedError
from vital_mapper.infrastructure.interop.gateway_adapter import HttpInteropGatewayAdapter
from vital_mapper.infrastructure.interop.patient_access_adapter import GatewayPatientAccessAdapter
from vital_mapper.infrastructure.persistence.repository import PostgresRepository
from vital_mapper.infrastructure.security.audit import log_access
from vital_mapper.infrastructure.security.auth import CurrentUser
from vital_mapper.infrastructure.security.rbac import check_patient_access, require_role
from vital_mapper.interfaces.api.deps import get_session
from vital_mapper.interfaces.api.schemas import ExtractionUpdateRequest

router = APIRouter(prefix="/extractions", tags=["extractions"])


@router.patch("/{extraction_id}")
async def update_extraction(
    extraction_id: uuid.UUID,
    body: ExtractionUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(require_role(UserRole.PFLEGEFACHKRAFT, UserRole.SCHICHTLEITUNG)),
) -> dict[str, Any]:
    """Speichert eine manuelle JSON-Korrektur vor der Freigabe (F-13/F-21)."""

    repository = PostgresRepository(session)
    patient_ref = await repository.get_patient_ref_for_extraction(extraction_id)
    try:
        if user.access_token:
            await GatewayPatientAccessAdapter(HttpInteropGatewayAdapter()).assert_access(
                patient_ref, user.access_token
            )
        else:
            await check_patient_access(user.subject, patient_ref, repository)
    except AccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff auf die Patientendokumentation.",
        ) from exc

    extraction = await UpdateClinicalExtractionUseCase(repository).execute(extraction_id, body.data)
    await log_access(user.subject, patient_ref, "update_clinical_extraction")
    return {
        "id": str(extraction.id),
        "transcript_id": str(extraction.transcript_id),
        "data": extraction.data.model_dump(mode="json"),
        "ollama_version": extraction.ollama_version,
    }
