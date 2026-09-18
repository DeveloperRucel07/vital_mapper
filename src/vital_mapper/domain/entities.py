from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from vital_mapper.domain.value_objects import ClinicalExtraction


class DraftStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    DISCARDED = "discarded"


class UserRole(StrEnum):
    PFLEGEFACHKRAFT = "pflegefachkraft"
    SCHICHTLEITUNG = "schichtleitung"
    ADMINISTRATOR = "administrator"
    QUALITAETSVERANTWORTLICHER = "qualitaetsverantwortlicher"
    DATENSCHUTZBEAUFTRAGTER = "datenschutzbeauftragter"


@dataclass
class User:
    """Authentifizierbares Benutzerkonto ohne Klartextpasswort (F-30)."""

    id: uuid.UUID
    username: str
    password_hash: str
    role: UserRole
    active: bool


@dataclass
class Recording:
    id: uuid.UUID
    patient_ref: str
    author_id: uuid.UUID
    audio_ref: str  # Verweis auf verschluesselt abgelegte Datei (F-26)
    started_at: datetime
    ended_at: datetime | None = None


@dataclass
class Transcript:
    id: uuid.UUID
    recording_id: uuid.UUID
    text: str
    confidence: float
    whisper_version: str
    created_at: datetime


@dataclass
class ExtractionResult:
    id: uuid.UUID
    transcript_id: uuid.UUID
    data: ClinicalExtraction
    ollama_version: str
    created_at: datetime


@dataclass
class CareReportDraft:
    id: uuid.UUID
    extraction_id: uuid.UUID
    report_text: str
    status: DraftStatus
    created_at: datetime
    updated_at: datetime


@dataclass
class TranscriptWorkspaceItem:
    """Nicht freigegebener Arbeitsstand eines Transkripts (F-15/UC-05)."""

    transcript: Transcript
    patient_ref: str
    recording_started_at: datetime
    extraction: ExtractionResult | None = None
    draft: CareReportDraft | None = None


@dataclass
class ApprovedDocumentation:
    """Freigegebene Daten fuer die nachgelagerte Interoperabilitaet (F-20)."""

    patient_ref: str
    report_text: str
    extraction: ClinicalExtraction
    recorded_at: datetime


@dataclass
class Correction:
    id: uuid.UUID
    draft_id: uuid.UUID
    field_path: str
    prediction: str
    correction: str
    corrected_by: uuid.UUID
    created_at: datetime


@dataclass
class Approval:
    id: uuid.UUID
    draft_id: uuid.UUID
    approved_by: uuid.UUID
    approved_at: datetime
    model_versions: dict[str, str]


@dataclass
class AccessGrant:
    """Vertretungszugriff bei Schichtuebergaben, siehe UC-09."""

    id: uuid.UUID
    user_id: uuid.UUID
    patient_ref: str
    granted_by: uuid.UUID
    valid_from: datetime
    valid_until: datetime
