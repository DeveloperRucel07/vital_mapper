import uuid

from pydantic import BaseModel, Field

from vital_mapper.domain.entities import UserRole
from vital_mapper.domain.value_objects import ClinicalExtraction


class ApproveDraftRequest(BaseModel):
    model_versions: dict[str, str]


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    draft_id: uuid.UUID
    approved_at: str


class CorrectionRequest(BaseModel):
    field_path: str = Field(min_length=1, max_length=200)
    prediction: str = Field(max_length=4000)
    correction: str = Field(max_length=4000)


class TranscriptReviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=100_000)


class ExtractionUpdateRequest(BaseModel):
    data: ClinicalExtraction


class DraftUpdateRequest(BaseModel):
    report_text: str = Field(min_length=1, max_length=100_000)


class LoginRequest(BaseModel):
    """Anmeldedaten; das Passwort wird weder gespeichert noch ausgegeben (F-30)."""

    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth2 response scheme, kein Secret


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=1, max_length=256)
    role: UserRole


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    role: UserRole
    active: bool
