import uuid
from datetime import UTC, datetime

import pytest

from vital_mapper.application.use_cases.create_recording import CreateRecordingUseCase
from vital_mapper.application.use_cases.transcribe_recording import TranscribeRecordingUseCase
from vital_mapper.domain.entities import Recording, Transcript
from vital_mapper.domain.exceptions import AudioRetentionExpiredError, RecordingNotFoundError


class FakeAccess:
    def __init__(self) -> None:
        self.patient_ref: str | None = None

    async def assert_access(self, patient_ref: str, access_token: str) -> None:
        self.patient_ref = patient_ref
        assert access_token


class FakeStorage:
    def __init__(self) -> None:
        self.audio: bytes | None = None
        self.ref = "recording.enc"

    async def store(self, recording_id, audio, content_type):
        assert content_type == "audio/webm"
        self.audio = audio
        return self.ref

    async def load(self, audio_ref):
        assert audio_ref == self.ref
        return self.audio or b""

    async def delete(self, audio_ref):
        self.audio = None


class FakeRepository:
    def __init__(self) -> None:
        self.recording: Recording | None = None
        self.transcript: Transcript | None = None

    async def save_recording(self, recording) -> None:
        self.recording = recording

    async def get_recording(self, recording_id):
        if self.recording is None:
            raise RecordingNotFoundError(str(recording_id))
        return self.recording

    async def save_transcript(self, transcript) -> None:
        self.transcript = transcript


class FakeTranscription:
    async def transcribe(self, audio: bytes, language: str = "de"):
        assert audio == b"synthetic audio"
        return "Puls 76", 0.98, "test-whisper"


class FakeEvents:
    async def publish(self, event) -> None:
        return None


async def test_recording_is_access_checked_and_stored_before_persistence() -> None:
    access = FakeAccess()
    storage = FakeStorage()
    repository = FakeRepository()
    recording = await CreateRecordingUseCase(repository, storage, access).execute(
        "demo-patient",
        uuid.uuid4(),
        "opaque-test-token",
        b"synthetic audio",
        "audio/webm",
        datetime.now(UTC),
        datetime.now(UTC),
    )

    assert access.patient_ref == "demo-patient"
    assert storage.audio == b"synthetic audio"
    assert repository.recording == recording
    assert recording.audio_ref == "recording.enc"


async def test_recording_replay_returns_the_original_recording() -> None:
    access = FakeAccess()
    storage = FakeStorage()
    repository = FakeRepository()
    recording_id = uuid.uuid4()
    first = await CreateRecordingUseCase(repository, storage, access).execute(
        "demo-patient",
        uuid.uuid4(),
        "opaque-test-token",
        b"synthetic audio",
        "audio/webm",
        datetime.now(UTC),
        datetime.now(UTC),
        recording_id,
    )
    replayed = await CreateRecordingUseCase(repository, storage, access).execute(
        "demo-patient",
        first.author_id,
        "opaque-test-token",
        b"synthetic audio",
        "audio/webm",
        datetime.now(UTC),
        datetime.now(UTC),
        recording_id,
    )

    assert replayed == first


async def test_transcription_loads_audio_bytes_from_storage() -> None:
    repository = FakeRepository()
    repository.recording = Recording(
        id=uuid.uuid4(),
        patient_ref="demo-patient",
        author_id=uuid.uuid4(),
        audio_ref="recording.enc",
        started_at=datetime.now(UTC),
    )
    storage = FakeStorage()
    storage.audio = b"synthetic audio"
    transcript = await TranscribeRecordingUseCase(
        FakeTranscription(), repository, storage, FakeEvents()
    ).execute(repository.recording.id)

    assert transcript.text == "Puls 76"
    assert repository.transcript == transcript


async def test_transcription_rejects_audio_removed_by_retention() -> None:
    repository = FakeRepository()
    repository.recording = Recording(
        id=uuid.uuid4(),
        patient_ref="demo-patient",
        author_id=uuid.uuid4(),
        audio_ref="",
        started_at=datetime.now(UTC),
    )

    with pytest.raises(AudioRetentionExpiredError):
        await TranscribeRecordingUseCase(
            FakeTranscription(), repository, FakeStorage(), FakeEvents()
        ).execute(repository.recording.id)
