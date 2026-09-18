import uuid
from abc import ABC, abstractmethod
from datetime import date, datetime

from vital_mapper.domain.entities import (
    Approval,
    ApprovedDocumentation,
    CareReportDraft,
    Correction,
    ExtractionResult,
    Recording,
    Transcript,
    TranscriptWorkspaceItem,
)
from vital_mapper.domain.events import DomainEvent
from vital_mapper.domain.value_objects import ClinicalExtraction


class RepositoryPort(ABC):
    @abstractmethod
    async def get_recording(self, recording_id: uuid.UUID) -> Recording: ...

    @abstractmethod
    async def get_patient_ref_for_draft(self, draft_id: uuid.UUID) -> str: ...

    @abstractmethod
    async def get_approved_documentation(self, draft_id: uuid.UUID) -> ApprovedDocumentation: ...

    @abstractmethod
    async def find_active_grant(
        self, user_id: str, patient_ref: str, now: datetime
    ) -> object | None: ...

    @abstractmethod
    async def save_recording(self, recording: Recording) -> None: ...

    @abstractmethod
    async def save_transcript(self, transcript: Transcript) -> None: ...

    @abstractmethod
    async def get_transcript(self, transcript_id: uuid.UUID) -> Transcript: ...

    @abstractmethod
    async def update_transcript_text(self, transcript_id: uuid.UUID, text: str) -> Transcript: ...

    @abstractmethod
    async def list_pending_transcripts(
        self, author_id: uuid.UUID, day: date
    ) -> list[TranscriptWorkspaceItem]: ...

    @abstractmethod
    async def save_extraction(self, extraction: ExtractionResult) -> None: ...

    @abstractmethod
    async def get_extraction(self, extraction_id: uuid.UUID) -> ExtractionResult: ...

    @abstractmethod
    async def get_patient_ref_for_extraction(self, extraction_id: uuid.UUID) -> str: ...

    @abstractmethod
    async def update_extraction_data(
        self, extraction_id: uuid.UUID, data: ClinicalExtraction
    ) -> ExtractionResult: ...

    @abstractmethod
    async def save_draft(self, draft: CareReportDraft) -> None: ...

    @abstractmethod
    async def get_draft(self, draft_id: uuid.UUID) -> CareReportDraft: ...

    @abstractmethod
    async def update_draft_text(self, draft_id: uuid.UUID, report_text: str) -> CareReportDraft: ...

    @abstractmethod
    async def save_correction(self, correction: Correction) -> None: ...

    @abstractmethod
    async def save_correction_and_enqueue_event(
        self, correction: Correction, event: DomainEvent
    ) -> None:
        """Speichert Korrektur und Outbox-Event atomar (F-21/F-39)."""

    @abstractmethod
    async def save_approval_and_enqueue_events(
        self, approval: Approval, draft: CareReportDraft, events: list[DomainEvent]
    ) -> None:
        """MUSS transaktional sein: Status-Aenderung + Approval + Outbox-Eintrag
        in einer DB-Transaktion (Konsistenzprinzip, Anforderungsdokument
        Kapitel 11.4). Kein Zwischen-Commit zwischen diesen drei Schritten."""
