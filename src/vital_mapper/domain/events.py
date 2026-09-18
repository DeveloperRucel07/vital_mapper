from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class EventType(StrEnum):
    RECORDING_COMPLETED = "RecordingCompleted"
    TRANSCRIPT_READY = "TranscriptReady"
    EXTRACTION_COMPLETED = "ExtractionCompleted"
    DOCUMENTATION_APPROVED = "DocumentationApproved"
    FHIR_SUBMISSION_SUCCEEDED = "FhirSubmissionSucceeded"
    FHIR_SUBMISSION_FAILED = "FhirSubmissionFailed"
    CORRECTION_RECORDED = "CorrectionRecorded"


class DomainEvent(BaseModel):
    id: uuid.UUID
    type: EventType
    occurred_at: datetime
    payload: dict[str, Any]
