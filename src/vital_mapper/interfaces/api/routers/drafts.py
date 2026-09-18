"""Endpunkte rund um Pflegebericht-Entwuerfe: Freigabe (UC-06) und Korrektur
(UC-05). Jede Route mit Patientenbezug MUSS ueber require_role abgesichert
sein (F-30/F-31) - siehe AGENTS.md, Abschnitt Security by Design."""

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from vital_mapper.application.use_cases.approve_documentation import (
    ApproveDocumentationUseCase,
)
from vital_mapper.application.use_cases.record_correction import RecordCorrectionUseCase
from vital_mapper.application.use_cases.submit_approved_documentation import (
    SubmitApprovedDocumentationUseCase,
)
from vital_mapper.application.use_cases.update_care_report_draft import UpdateCareReportDraftUseCase
from vital_mapper.domain.entities import UserRole
from vital_mapper.domain.exceptions import AccessDeniedError
from vital_mapper.infrastructure.interop.gateway_adapter import (
    HttpInteropGatewayAdapter,
    InteropGatewayError,
)
from vital_mapper.infrastructure.interop.nursing_report_adapter import GatewayNursingReportAdapter
from vital_mapper.infrastructure.interop.patient_access_adapter import GatewayPatientAccessAdapter
from vital_mapper.infrastructure.persistence.repository import PostgresRepository
from vital_mapper.infrastructure.security.audit import log_access
from vital_mapper.infrastructure.security.auth import CurrentUser
from vital_mapper.infrastructure.security.rbac import check_patient_access, require_role
from vital_mapper.interfaces.api.deps import get_session
from vital_mapper.interfaces.api.schemas import (
    ApproveDraftRequest,
    CorrectionRequest,
    DraftUpdateRequest,
)

router = APIRouter(prefix="/drafts", tags=["drafts"])
logger = structlog.get_logger("drafts")


async def _assert_patient_access(
    repository: PostgresRepository, draft_id: uuid.UUID, user: CurrentUser, action: str
) -> str:
    """Prueft den Patientenzugriff und protokolliert ihn (F-31/F-33)."""
    patient_ref = await repository.get_patient_ref_for_draft(draft_id)
    try:
        if user.access_token:
            await GatewayPatientAccessAdapter(HttpInteropGatewayAdapter()).assert_access(
                patient_ref, user.access_token
            )
        else:
            await check_patient_access(user.subject, patient_ref, repository)
    except AccessDeniedError as exc:
        # Die Domänenausnahme wird bewusst an der API-Grenze in HTTP 403 übersetzt.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff auf die Patientendokumentation.",
        ) from exc
    await log_access(user.subject, patient_ref, action)
    return patient_ref


@router.post("/{draft_id}/approve")
async def approve_draft(
    draft_id: uuid.UUID,
    body: ApproveDraftRequest,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(require_role(UserRole.PFLEGEFACHKRAFT, UserRole.SCHICHTLEITUNG)),
) -> dict[str, Any]:
    repository = PostgresRepository(session)
    patient_ref = await _assert_patient_access(repository, draft_id, user, "approve_draft")
    use_case = ApproveDocumentationUseCase(repository)
    approval = await use_case.execute(draft_id, user.id, body.model_versions)
    submission_status = "submitted"
    submission_resource_id: str | None = None
    if user.access_token:
        try:
            result = await SubmitApprovedDocumentationUseCase(
                repository, GatewayNursingReportAdapter()
            ).execute(draft_id, user.access_token)
            report_result = result.get("report")
            resource_id = (
                report_result.get("id") if isinstance(report_result, dict) else result.get("id")
            )
            submission_resource_id = resource_id if isinstance(resource_id, str) else None
        except InteropGatewayError as exc:
            submission_status = "failed"
            logger.error(
                "approved_documentation_submission_failed",
                draft_id=str(draft_id),
                patient_ref=patient_ref,
                error=str(exc),
            )
    else:
        submission_status = "failed"
        logger.error(
            "approved_documentation_submission_failed",
            draft_id=str(draft_id),
            patient_ref=patient_ref,
            error="missing_oidc_access_token",
        )
    response: dict[str, Any] = {
        "id": str(approval.id),
        "draft_id": str(draft_id),
        "approved_at": approval.approved_at.isoformat(),
        "submission_status": submission_status,
    }
    if submission_resource_id is not None:
        response["monitoring_resource_id"] = submission_resource_id
    return response


@router.get("/{draft_id}")
async def get_draft(
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(require_role(UserRole.PFLEGEFACHKRAFT, UserRole.SCHICHTLEITUNG)),
) -> dict[str, str]:
    repository = PostgresRepository(session)
    await _assert_patient_access(repository, draft_id, user, "read_draft")
    draft = await repository.get_draft(draft_id)
    return {
        "id": str(draft.id),
        "extraction_id": str(draft.extraction_id),
        "report_text": draft.report_text,
        "status": draft.status.value,
        "created_at": draft.created_at.isoformat(),
        "updated_at": draft.updated_at.isoformat(),
    }


@router.patch("/{draft_id}")
async def update_draft(
    draft_id: uuid.UUID,
    body: DraftUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(require_role(UserRole.PFLEGEFACHKRAFT, UserRole.SCHICHTLEITUNG)),
) -> dict[str, str]:
    repository = PostgresRepository(session)
    patient_ref = await _assert_patient_access(repository, draft_id, user, "update_draft")
    draft = await UpdateCareReportDraftUseCase(repository).execute(draft_id, body.report_text)
    await log_access(user.subject, patient_ref, "update_draft")
    return {
        "id": str(draft.id),
        "extraction_id": str(draft.extraction_id),
        "report_text": draft.report_text,
        "status": draft.status.value,
        "created_at": draft.created_at.isoformat(),
        "updated_at": draft.updated_at.isoformat(),
    }


@router.post("/{draft_id}/corrections")
async def add_correction(
    draft_id: uuid.UUID,
    body: CorrectionRequest,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(require_role(UserRole.PFLEGEFACHKRAFT)),
) -> dict[str, str]:
    repository = PostgresRepository(session)
    await _assert_patient_access(repository, draft_id, user, "record_correction")
    use_case = RecordCorrectionUseCase(repository)
    correction = await use_case.execute(
        draft_id, body.field_path, body.prediction, body.correction, user.id
    )
    return {"id": str(correction.id)}
