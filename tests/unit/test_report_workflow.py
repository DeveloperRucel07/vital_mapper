import uuid
from datetime import UTC, datetime

from vital_mapper.application.use_cases.create_care_report_draft import (
    CreateCareReportDraftUseCase,
)
from vital_mapper.application.use_cases.update_care_report_draft import (
    UpdateCareReportDraftUseCase,
)
from vital_mapper.domain.entities import CareReportDraft, DraftStatus, ExtractionResult, Transcript
from vital_mapper.domain.value_objects import ClinicalExtraction


class FakeDraftRepository:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.transcript = Transcript(
            id=uuid.uuid4(),
            recording_id=uuid.uuid4(),
            text="Puls 76",
            confidence=0.9,
            whisper_version="test-whisper",
            created_at=now,
        )
        self.extraction = ExtractionResult(
            id=uuid.uuid4(),
            transcript_id=self.transcript.id,
            data=ClinicalExtraction(),
            ollama_version="test-ollama",
            created_at=now,
        )
        self.draft: CareReportDraft | None = None

    async def get_extraction(self, extraction_id):
        return self.extraction

    async def get_transcript(self, transcript_id):
        return self.transcript

    async def save_draft(self, draft):
        self.draft = draft

    async def get_draft(self, draft_id):
        assert self.draft is not None
        return self.draft

    async def update_draft_text(self, draft_id, report_text):
        assert self.draft is not None
        self.draft.report_text = report_text
        self.draft.updated_at = datetime.now(UTC)
        return self.draft


async def test_report_draft_stays_bound_to_transcript() -> None:
    repository = FakeDraftRepository()
    draft = await CreateCareReportDraftUseCase(repository).execute(repository.extraction.id)

    assert draft.report_text == repository.transcript.text
    assert draft.status == DraftStatus.DRAFT


async def test_report_draft_can_be_edited_before_approval() -> None:
    repository = FakeDraftRepository()
    repository.draft = CareReportDraft(
        id=uuid.uuid4(),
        extraction_id=repository.extraction.id,
        report_text="Puls 76",
        status=DraftStatus.DRAFT,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    updated = await UpdateCareReportDraftUseCase(repository).execute(
        repository.draft.id, "Puls 76, Kontrolle erfolgt."
    )

    assert updated.report_text == "Puls 76, Kontrolle erfolgt."
