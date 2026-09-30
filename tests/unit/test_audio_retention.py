import uuid
from datetime import UTC, datetime, timedelta

import pytest

from vital_mapper.application.use_cases.enforce_audio_retention import (
    EnforceAudioRetentionUseCase,
)
from vital_mapper.domain.entities import Recording


class FakeRetentionRepository:
    def __init__(self, recordings: list[Recording]) -> None:
        self.recordings = recordings
        self.marked: list[uuid.UUID] = []

    async def list_recordings_with_expired_audio(
        self, cutoff: datetime, limit: int
    ) -> list[Recording]:
        return [
            recording
            for recording in self.recordings
            if recording.audio_ref and (recording.ended_at or recording.started_at) < cutoff
        ][:limit]

    async def mark_audio_deleted(self, recording_id: uuid.UUID) -> None:
        self.marked.append(recording_id)
        for recording in self.recordings:
            if recording.id == recording_id:
                recording.audio_ref = ""


class FakeAudioStorage:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def delete(self, audio_ref: str) -> None:
        self.deleted.append(audio_ref)


def _recording(*, age_days: int, audio_ref: str) -> Recording:
    now = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
    return Recording(
        id=uuid.uuid4(),
        patient_ref="synthetic-patient-retention",
        author_id=uuid.uuid4(),
        audio_ref=audio_ref,
        started_at=now - timedelta(days=age_days),
        ended_at=now - timedelta(days=age_days),
    )


async def test_expired_audio_is_deleted_and_reference_is_cleared() -> None:
    expired = _recording(age_days=31, audio_ref="expired.webm.enc")
    current = _recording(age_days=5, audio_ref="current.webm.enc")
    repository = FakeRetentionRepository([expired, current])
    storage = FakeAudioStorage()

    deleted = await EnforceAudioRetentionUseCase(
        repository,  # type: ignore[arg-type]
        storage,  # type: ignore[arg-type]
        retention_days=30,
    ).execute(now=datetime(2026, 9, 29, 12, 0, tzinfo=UTC))

    assert deleted == [expired]
    assert storage.deleted == ["expired.webm.enc"]
    assert repository.marked == [expired.id]
    assert expired.audio_ref == ""
    assert current.audio_ref == "current.webm.enc"


async def test_retention_rejects_naive_reference_time() -> None:
    use_case = EnforceAudioRetentionUseCase(
        FakeRetentionRepository([]),  # type: ignore[arg-type]
        FakeAudioStorage(),  # type: ignore[arg-type]
        retention_days=30,
    )

    with pytest.raises(ValueError, match="Zeitzone"):
        await use_case.execute(now=datetime(2026, 9, 29))
