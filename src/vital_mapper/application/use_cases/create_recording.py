from __future__ import annotations

import uuid
from datetime import datetime

from vital_mapper.application.ports.audio_storage_port import AudioStoragePort
from vital_mapper.application.ports.patient_access_port import PatientAccessPort
from vital_mapper.application.ports.repository_port import RepositoryPort
from vital_mapper.domain.entities import Recording
from vital_mapper.domain.exceptions import AccessDeniedError, RecordingNotFoundError


class CreateRecordingUseCase:
    """Legt eine geschuetzte Aufnahme mit Patientenkontext an (F-26/F-31)."""

    def __init__(
        self,
        repository: RepositoryPort,
        audio_storage: AudioStoragePort,
        patient_access: PatientAccessPort,
    ) -> None:
        self._repository = repository
        self._audio_storage = audio_storage
        self._patient_access = patient_access

    async def execute(
        self,
        patient_ref: str,
        author_id: uuid.UUID,
        access_token: str,
        audio: bytes,
        content_type: str,
        started_at: datetime,
        ended_at: datetime,
        recording_id: uuid.UUID | None = None,
    ) -> Recording:
        await self._patient_access.assert_access(patient_ref, access_token)
        requested_id = recording_id or uuid.uuid4()
        try:
            existing = await self._repository.get_recording(requested_id)
        except RecordingNotFoundError:
            existing = None
        if existing is not None:
            if existing.patient_ref != patient_ref or existing.author_id != author_id:
                raise AccessDeniedError(
                    "Aufnahme-ID darf nicht fuer einen anderen Kontext verwendet werden."
                )
            return existing

        recording = Recording(
            id=requested_id,
            patient_ref=patient_ref,
            author_id=author_id,
            audio_ref="",
            started_at=started_at,
            ended_at=ended_at,
        )
        audio_ref = await self._audio_storage.store(recording.id, audio, content_type)
        recording.audio_ref = audio_ref
        try:
            await self._repository.save_recording(recording)
        except Exception:
            await self._audio_storage.delete(audio_ref)
            raise
        return recording
