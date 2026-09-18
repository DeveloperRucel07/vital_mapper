from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vital_mapper.application.ports.repository_port import RepositoryPort
from vital_mapper.domain.entities import (
    Approval,
    ApprovedDocumentation,
    CareReportDraft,
    Correction,
    DraftStatus,
    ExtractionResult,
    Recording,
    Transcript,
    TranscriptWorkspaceItem,
)
from vital_mapper.domain.events import DomainEvent
from vital_mapper.domain.exceptions import (
    DraftNotFoundError,
    ExtractionNotFoundError,
    RecordingNotFoundError,
    TranscriptNotFoundError,
)
from vital_mapper.domain.value_objects import ClinicalExtraction
from vital_mapper.infrastructure.persistence.models import (
    AccessGrantModel,
    ApprovalModel,
    CareReportDraftModel,
    CorrectionModel,
    ExtractionModel,
    OutboxEventModel,
    RecordingModel,
    TranscriptModel,
)


class PostgresRepository(RepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_recording(self, recording: Recording) -> None:
        self._session.add(
            RecordingModel(
                id=recording.id,
                patient_ref=recording.patient_ref,
                author_id=recording.author_id,
                audio_ref=recording.audio_ref,
                started_at=recording.started_at,
                ended_at=recording.ended_at,
            )
        )
        await self._session.commit()

    async def get_recording(self, recording_id: uuid.UUID) -> Recording:
        model = await self._session.get(RecordingModel, recording_id)
        if model is None:
            raise RecordingNotFoundError(f"Recording {recording_id} nicht gefunden.")
        return Recording(
            id=model.id,
            patient_ref=model.patient_ref,
            author_id=model.author_id,
            audio_ref=model.audio_ref,
            started_at=model.started_at,
            ended_at=model.ended_at,
        )

    async def get_patient_ref_for_draft(self, draft_id: uuid.UUID) -> str:
        """Ermittelt den Patientenverweis ohne Stammdaten zu duplizieren (F-31)."""
        statement = (
            select(RecordingModel.patient_ref)
            .join(TranscriptModel, TranscriptModel.recording_id == RecordingModel.id)
            .join(ExtractionModel, ExtractionModel.transcript_id == TranscriptModel.id)
            .join(CareReportDraftModel, CareReportDraftModel.extraction_id == ExtractionModel.id)
            .where(CareReportDraftModel.id == draft_id)
        )
        patient_ref = await self._session.scalar(statement)
        if not isinstance(patient_ref, str):
            raise DraftNotFoundError(f"Draft {draft_id} nicht gefunden.")
        return patient_ref

    async def get_approved_documentation(self, draft_id: uuid.UUID) -> ApprovedDocumentation:
        """Laedt nur den freigegebenen Bericht und die Extraktion fuer die Uebergabe (F-20)."""
        statement = (
            select(
                RecordingModel.patient_ref,
                CareReportDraftModel.report_text,
                ExtractionModel.structured_data,
                RecordingModel.started_at,
            )
            .join(ExtractionModel, CareReportDraftModel.extraction_id == ExtractionModel.id)
            .join(TranscriptModel, ExtractionModel.transcript_id == TranscriptModel.id)
            .join(RecordingModel, TranscriptModel.recording_id == RecordingModel.id)
            .where(
                CareReportDraftModel.id == draft_id,
                CareReportDraftModel.status == DraftStatus.APPROVED.value,
            )
        )
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            raise DraftNotFoundError(f"Freigegebener Draft {draft_id} nicht gefunden.")
        patient_ref, report_text, structured_data, recording_started_at = row
        return ApprovedDocumentation(
            patient_ref=str(patient_ref),
            report_text=str(report_text),
            extraction=ClinicalExtraction.model_validate(structured_data),
            recorded_at=recording_started_at,
        )

    async def find_active_grant(
        self, user_id: str, patient_ref: str, now: datetime
    ) -> object | None:
        """Liest nur einen zum Zeitpunkt gueltigen Vertretungsgrant (F-31/F-32)."""
        statement = select(AccessGrantModel).where(
            AccessGrantModel.user_id == uuid.UUID(user_id),
            AccessGrantModel.patient_ref == patient_ref,
            AccessGrantModel.valid_from <= now,
            AccessGrantModel.valid_until >= now,
        )
        return cast(object | None, await self._session.scalar(statement))

    async def save_transcript(self, transcript: Transcript) -> None:
        self._session.add(
            TranscriptModel(
                id=transcript.id,
                recording_id=transcript.recording_id,
                text=transcript.text,
                confidence=transcript.confidence,
                whisper_version=transcript.whisper_version,
                created_at=transcript.created_at,
            )
        )
        await self._session.commit()

    async def get_transcript(self, transcript_id: uuid.UUID) -> Transcript:
        model = await self._session.get(TranscriptModel, transcript_id)
        if model is None:
            raise TranscriptNotFoundError(f"Transcript {transcript_id} nicht gefunden.")
        return Transcript(
            id=model.id,
            recording_id=model.recording_id,
            text=model.text,
            confidence=model.confidence,
            whisper_version=model.whisper_version,
            created_at=model.created_at,
        )

    async def update_transcript_text(self, transcript_id: uuid.UUID, text: str) -> Transcript:
        model = await self._session.get(TranscriptModel, transcript_id)
        if model is None:
            raise TranscriptNotFoundError(f"Transcript {transcript_id} nicht gefunden.")
        model.text = text
        await self._session.commit()
        return Transcript(
            id=model.id,
            recording_id=model.recording_id,
            text=model.text,
            confidence=model.confidence,
            whisper_version=model.whisper_version,
            created_at=model.created_at,
        )

    async def list_pending_transcripts(
        self, author_id: uuid.UUID, day: date
    ) -> list[TranscriptWorkspaceItem]:
        """Liefert die offenen Arbeitsstaende eines Nutzers fuer einen UTC-Tag (F-15/UC-05).

        Audio, Patientennamen und andere Stammdaten werden nicht zurueckgegeben. Gibt es
        mehrere Extraktionsversuche, wird nur der juengste Versuch angezeigt.
        """
        day_start = datetime.combine(day, time.min, tzinfo=UTC)
        next_day = day_start + timedelta(days=1)
        statement = (
            select(TranscriptModel, RecordingModel, ExtractionModel, CareReportDraftModel)
            .join(RecordingModel, TranscriptModel.recording_id == RecordingModel.id)
            .outerjoin(ExtractionModel, ExtractionModel.transcript_id == TranscriptModel.id)
            .outerjoin(
                CareReportDraftModel,
                CareReportDraftModel.extraction_id == ExtractionModel.id,
            )
            .where(
                RecordingModel.author_id == author_id,
                RecordingModel.started_at >= day_start,
                RecordingModel.started_at < next_day,
            )
            .order_by(
                RecordingModel.started_at.desc(),
                TranscriptModel.created_at.desc(),
                ExtractionModel.created_at.desc().nulls_last(),
            )
        )
        rows = (await self._session.execute(statement)).all()
        items: list[TranscriptWorkspaceItem] = []
        seen_transcripts: set[uuid.UUID] = set()
        for transcript_model, recording_model, extraction_model, draft_model in rows:
            if transcript_model.id in seen_transcripts:
                continue
            seen_transcripts.add(transcript_model.id)
            draft = self._draft_from_model(draft_model) if draft_model is not None else None
            if draft is not None and draft.status.value in {"approved", "discarded"}:
                continue
            extraction = (
                self._extraction_from_model(extraction_model)
                if extraction_model is not None
                else None
            )
            items.append(
                TranscriptWorkspaceItem(
                    transcript=self._transcript_from_model(transcript_model),
                    patient_ref=recording_model.patient_ref,
                    recording_started_at=recording_model.started_at,
                    extraction=extraction,
                    draft=draft,
                )
            )
        return items

    async def save_extraction(self, extraction: ExtractionResult) -> None:
        self._session.add(
            ExtractionModel(
                id=extraction.id,
                transcript_id=extraction.transcript_id,
                structured_data=extraction.data.model_dump(mode="json"),
                unsichere_felder=extraction.data.unsichere_felder,
                ollama_version=extraction.ollama_version,
                created_at=extraction.created_at,
            )
        )
        await self._session.commit()

    async def get_extraction(self, extraction_id: uuid.UUID) -> ExtractionResult:
        model = await self._session.get(ExtractionModel, extraction_id)
        if model is None:
            raise ExtractionNotFoundError(f"Extraction {extraction_id} nicht gefunden.")
        return self._extraction_from_model(model)

    async def get_patient_ref_for_extraction(self, extraction_id: uuid.UUID) -> str:
        statement = (
            select(RecordingModel.patient_ref)
            .join(TranscriptModel, TranscriptModel.recording_id == RecordingModel.id)
            .join(ExtractionModel, ExtractionModel.transcript_id == TranscriptModel.id)
            .where(ExtractionModel.id == extraction_id)
        )
        patient_ref = (await self._session.execute(statement)).scalar_one_or_none()
        if patient_ref is None:
            raise ExtractionNotFoundError(f"Extraction {extraction_id} nicht gefunden.")
        return str(patient_ref)

    async def update_extraction_data(
        self, extraction_id: uuid.UUID, data: ClinicalExtraction
    ) -> ExtractionResult:
        model = await self._session.get(ExtractionModel, extraction_id)
        if model is None:
            raise ExtractionNotFoundError(f"Extraction {extraction_id} nicht gefunden.")
        model.structured_data = data.model_dump(mode="json")
        model.unsichere_felder = data.unsichere_felder
        await self._session.commit()
        return self._extraction_from_model(model, data=data)

    async def save_draft(self, draft: CareReportDraft) -> None:
        self._session.add(
            CareReportDraftModel(
                id=draft.id,
                extraction_id=draft.extraction_id,
                report_text=draft.report_text,
                status=draft.status.value,
                created_at=draft.created_at,
                updated_at=draft.updated_at,
            )
        )
        await self._session.commit()

    async def get_draft(self, draft_id: uuid.UUID) -> CareReportDraft:
        model = await self._session.get(CareReportDraftModel, draft_id)
        if model is None:
            raise DraftNotFoundError(f"Draft {draft_id} nicht gefunden.")
        return self._draft_from_model(model)

    async def update_draft_text(self, draft_id: uuid.UUID, report_text: str) -> CareReportDraft:
        model = await self._session.get(CareReportDraftModel, draft_id)
        if model is None:
            raise DraftNotFoundError(f"Draft {draft_id} nicht gefunden.")
        model.report_text = report_text
        model.updated_at = datetime.now(UTC)
        await self._session.commit()
        return self._draft_from_model(model)

    @staticmethod
    def _transcript_from_model(model: TranscriptModel) -> Transcript:
        return Transcript(
            id=model.id,
            recording_id=model.recording_id,
            text=model.text,
            confidence=model.confidence,
            whisper_version=model.whisper_version,
            created_at=model.created_at,
        )

    @staticmethod
    def _extraction_from_model(
        model: ExtractionModel, data: ClinicalExtraction | None = None
    ) -> ExtractionResult:
        return ExtractionResult(
            id=model.id,
            transcript_id=model.transcript_id,
            data=data or ClinicalExtraction.model_validate(model.structured_data),
            ollama_version=model.ollama_version,
            created_at=model.created_at,
        )

    @staticmethod
    def _draft_from_model(model: CareReportDraftModel) -> CareReportDraft:
        return CareReportDraft(
            id=model.id,
            extraction_id=model.extraction_id,
            report_text=model.report_text,
            status=DraftStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def save_correction(self, correction: Correction) -> None:
        self._session.add(
            CorrectionModel(
                id=correction.id,
                draft_id=correction.draft_id,
                field_path=correction.field_path,
                prediction=correction.prediction,
                correction=correction.correction,
                corrected_by=correction.corrected_by,
                created_at=correction.created_at,
            )
        )
        await self._session.commit()

    async def save_correction_and_enqueue_event(
        self, correction: Correction, event: DomainEvent
    ) -> None:
        """Schreibt Korrektur und Outbox-Event in einer Transaktion (F-21/F-39)."""
        self._session.add(
            CorrectionModel(
                id=correction.id,
                draft_id=correction.draft_id,
                field_path=correction.field_path,
                prediction=correction.prediction,
                correction=correction.correction,
                corrected_by=correction.corrected_by,
                created_at=correction.created_at,
            )
        )
        self._session.add(
            OutboxEventModel(
                id=event.id,
                event_type=event.type.value,
                payload=event.payload,
                status="pending",
                created_at=event.occurred_at,
            )
        )
        await self._session.commit()

    async def save_approval_and_enqueue_events(
        self, approval: Approval, draft: CareReportDraft, events: list[DomainEvent]
    ) -> None:
        """Konsistenzprinzip (Kapitel 11.4): Draft-Status, Approval und
        Outbox-Events werden in EINER Transaktion committet - kein separates
        commit() pro Schritt. Schlaegt einer der drei Schreibvorgaenge fehl,
        rollt die gesamte Transaktion zurueck."""
        draft_model = await self._session.get(CareReportDraftModel, draft.id)
        if draft_model is None:
            raise DraftNotFoundError(f"Draft {draft.id} nicht gefunden.")
        draft_model.status = draft.status.value
        draft_model.updated_at = draft.updated_at

        self._session.add(
            ApprovalModel(
                id=approval.id,
                draft_id=approval.draft_id,
                approved_by=approval.approved_by,
                approved_at=approval.approved_at,
                model_versions=approval.model_versions,
            )
        )

        for event in events:
            self._session.add(
                OutboxEventModel(
                    id=event.id,
                    event_type=event.type.value,
                    payload=event.payload,
                    status="pending",
                    created_at=datetime.now(UTC),
                )
            )

        await self._session.commit()
