from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from vital_mapper.application.use_cases.create_care_report_draft import (
    CreateCareReportDraftUseCase,
)
from vital_mapper.application.use_cases.create_recording import CreateRecordingUseCase
from vital_mapper.application.use_cases.extract_clinical_data import ExtractClinicalDataUseCase
from vital_mapper.application.use_cases.transcribe_recording import TranscribeRecordingUseCase
from vital_mapper.config import settings
from vital_mapper.domain.entities import UserRole
from vital_mapper.domain.exceptions import AccessDeniedError
from vital_mapper.infrastructure.events.redis_event_bus import RedisEventBus
from vital_mapper.infrastructure.interop.gateway_adapter import HttpInteropGatewayAdapter
from vital_mapper.infrastructure.interop.patient_access_adapter import GatewayPatientAccessAdapter
from vital_mapper.infrastructure.ollama.ollama_adapter import OllamaExtractionAdapter
from vital_mapper.infrastructure.persistence.repository import PostgresRepository
from vital_mapper.infrastructure.security.audio_storage import EncryptedAudioStorage
from vital_mapper.infrastructure.security.audit import log_access
from vital_mapper.infrastructure.security.auth import CurrentUser
from vital_mapper.infrastructure.security.rbac import require_role
from vital_mapper.infrastructure.whisper.whisper_adapter import WhisperTranscriptionAdapter
from vital_mapper.interfaces.api.deps import get_session
from vital_mapper.interfaces.api.routers.interop import PatientContextRequest
from vital_mapper.interfaces.api.schemas import TranscriptReviewRequest

router = APIRouter(tags=["recordings"])


def _patient_access() -> GatewayPatientAccessAdapter:
    return GatewayPatientAccessAdapter(HttpInteropGatewayAdapter())


def _require_token(user: CurrentUser) -> str:
    if not user.access_token:
        raise HTTPException(status_code=401, detail="OIDC-Sitzung erforderlich.")
    return user.access_token


def _map_access_error(exc: AccessDeniedError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Kein Zugriff auf den Patientenkontext.",
    )


@router.post("/recordings")
async def create_recording(
    patient_ref: str = Form(...),
    started_at: datetime | None = Form(default=None),
    audio: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(require_role(UserRole.PFLEGEFACHKRAFT, UserRole.SCHICHTLEITUNG)),
) -> dict[str, str]:
    try:
        patient = PatientContextRequest(patient_ref=patient_ref)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Ungueltiger Patientenkontext.") from exc
    content_type = (audio.content_type or "").split(";", 1)[0].strip().lower()
    allowed_types = {
        "audio/webm",
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/ogg",
        "audio/mp4",
    }
    if content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Nicht unterstuetztes Audioformat.")
    data = await audio.read(settings.max_audio_bytes + 1)
    if len(data) > settings.max_audio_bytes:
        raise HTTPException(status_code=413, detail="Die Aufnahme ist zu gross.")
    start = started_at or datetime.now(UTC)
    end = datetime.now(UTC)
    repository = PostgresRepository(session)
    try:
        recording = await CreateRecordingUseCase(
            repository, EncryptedAudioStorage(settings.audio_storage_path), _patient_access()
        ).execute(
            patient.patient_ref,
            user.id,
            _require_token(user),
            data,
            content_type,
            start,
            end,
        )
    except AccessDeniedError as exc:
        raise _map_access_error(exc) from exc
    await log_access(user.subject, patient.patient_ref, "upload_recording")
    return {
        "id": str(recording.id),
        "patient_ref": recording.patient_ref,
        "started_at": recording.started_at.isoformat(),
        "ended_at": (recording.ended_at or end).isoformat(),
        "status": "uploaded",
    }


@router.post("/recordings/{recording_id}/transcribe")
async def transcribe_recording(
    recording_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(require_role(UserRole.PFLEGEFACHKRAFT, UserRole.SCHICHTLEITUNG)),
) -> dict[str, Any]:
    repository = PostgresRepository(session)
    recording = await repository.get_recording(recording_id)
    try:
        await _patient_access().assert_access(recording.patient_ref, _require_token(user))
    except AccessDeniedError as exc:
        raise _map_access_error(exc) from exc
    transcript = await TranscribeRecordingUseCase(
        WhisperTranscriptionAdapter(settings.whisper_base_url),
        repository,
        EncryptedAudioStorage(settings.audio_storage_path),
        RedisEventBus(settings.redis_url),
    ).execute(recording_id)
    await log_access(user.subject, recording.patient_ref, "transcribe_recording")
    return {
        "id": str(transcript.id),
        "recording_id": str(transcript.recording_id),
        "text": transcript.text,
        "confidence": transcript.confidence,
        "whisper_version": transcript.whisper_version,
    }


@router.post("/transcripts/{transcript_id}/extract")
async def extract_transcript(
    transcript_id: uuid.UUID,
    body: TranscriptReviewRequest,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(require_role(UserRole.PFLEGEFACHKRAFT, UserRole.SCHICHTLEITUNG)),
) -> dict[str, Any]:
    repository = PostgresRepository(session)
    transcript = await repository.get_transcript(transcript_id)
    recording = await repository.get_recording(transcript.recording_id)
    try:
        await _patient_access().assert_access(recording.patient_ref, _require_token(user))
    except AccessDeniedError as exc:
        raise _map_access_error(exc) from exc
    extraction = await ExtractClinicalDataUseCase(
        OllamaExtractionAdapter(settings.ollama_base_url, settings.ollama_model),
        repository,
        RedisEventBus(settings.redis_url),
    ).execute(transcript_id, body.text)
    draft = await CreateCareReportDraftUseCase(repository).execute(extraction.id)
    await log_access(user.subject, recording.patient_ref, "extract_clinical_data")
    return {
        "id": str(extraction.id),
        "transcript_id": str(extraction.transcript_id),
        "data": extraction.data.model_dump(mode="json"),
        "ollama_version": extraction.ollama_version,
        "draft": {
            "id": str(draft.id),
            "extraction_id": str(draft.extraction_id),
            "report_text": draft.report_text,
            "status": draft.status.value,
            "created_at": draft.created_at.isoformat(),
            "updated_at": draft.updated_at.isoformat(),
        },
    }
