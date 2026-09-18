"""Arbeitsliste fuer gespeicherte, noch nicht freigegebene Transkripte (UC-05)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from vital_mapper.domain.entities import UserRole
from vital_mapper.domain.exceptions import AccessDeniedError
from vital_mapper.infrastructure.interop.gateway_adapter import HttpInteropGatewayAdapter
from vital_mapper.infrastructure.interop.patient_access_adapter import GatewayPatientAccessAdapter
from vital_mapper.infrastructure.persistence.repository import PostgresRepository
from vital_mapper.infrastructure.security.audit import log_access
from vital_mapper.infrastructure.security.auth import CurrentUser
from vital_mapper.infrastructure.security.rbac import check_patient_access, require_role
from vital_mapper.interfaces.api.deps import get_session

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


@router.get("/workspace")
async def list_transcript_workspace(
    day: date | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(require_role(UserRole.PFLEGEFACHKRAFT, UserRole.SCHICHTLEITUNG)),
) -> dict[str, Any]:
    """Listet nur eigene offene Transkripte fuer einen Tag (F-15/F-30/F-31)."""
    selected_day = day or datetime.now(UTC).date()
    repository = PostgresRepository(session)
    items = await repository.list_pending_transcripts(user.id, selected_day)
    visible_items: list[dict[str, Any]] = []
    for item in items:
        try:
            if user.access_token:
                await GatewayPatientAccessAdapter(HttpInteropGatewayAdapter()).assert_access(
                    item.patient_ref, user.access_token
                )
            else:
                await check_patient_access(user.subject, item.patient_ref, repository)
        except AccessDeniedError:
            # Kein Hinweis darauf, dass ein Patientenkontext existiert.
            continue
        await log_access(user.subject, item.patient_ref, "list_transcript_workspace")
        extraction = item.extraction
        draft = item.draft
        visible_items.append(
            {
                "transcript": {
                    "id": str(item.transcript.id),
                    "recording_id": str(item.transcript.recording_id),
                    "text": item.transcript.text,
                    "confidence": item.transcript.confidence,
                    "whisper_version": item.transcript.whisper_version,
                },
                "patient_ref": item.patient_ref,
                "recording_started_at": item.recording_started_at.isoformat(),
                "extraction": (
                    {
                        "id": str(extraction.id),
                        "transcript_id": str(extraction.transcript_id),
                        "data": extraction.data.model_dump(mode="json"),
                        "ollama_version": extraction.ollama_version,
                    }
                    if extraction is not None
                    else None
                ),
                "draft": (
                    {
                        "id": str(draft.id),
                        "extraction_id": str(draft.extraction_id),
                        "report_text": draft.report_text,
                        "status": draft.status.value,
                        "created_at": draft.created_at.isoformat(),
                        "updated_at": draft.updated_at.isoformat(),
                    }
                    if draft is not None
                    else None
                ),
            }
        )
    return {"day": selected_day.isoformat(), "items": visible_items}
