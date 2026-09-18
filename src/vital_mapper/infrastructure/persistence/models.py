from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    """Benutzerkonto; nur der Passwort-Hash wird gespeichert (F-30)."""

    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class RecordingModel(Base):
    __tablename__ = "recordings"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_ref: Mapped[str] = mapped_column(String, index=True)
    author_id: Mapped[uuid.UUID]
    # Pfad/Referenz auf verschluesselt abgelegte Audiodatei, siehe
    # infrastructure/security/encryption.py (F-26)
    audio_ref: Mapped[str]
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TranscriptModel(Base):
    __tablename__ = "transcripts"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recording_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recordings.id"))
    text: Mapped[str]
    confidence: Mapped[float] = mapped_column(Float)
    whisper_version: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExtractionModel(Base):
    __tablename__ = "extractions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    transcript_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transcripts.id"))
    structured_data: Mapped[dict[str, Any]] = mapped_column(JSON)
    unsichere_felder: Mapped[list[str]] = mapped_column(JSON, default=list)
    ollama_version: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CareReportDraftModel(Base):
    __tablename__ = "care_report_drafts"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    extraction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("extractions.id"))
    report_text: Mapped[str]
    status: Mapped[str] = mapped_column(String, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CorrectionModel(Base):
    __tablename__ = "corrections"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    draft_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("care_report_drafts.id"))
    field_path: Mapped[str]
    prediction: Mapped[str]
    correction: Mapped[str]
    corrected_by: Mapped[uuid.UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ApprovalModel(Base):
    __tablename__ = "approvals"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    draft_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("care_report_drafts.id"))
    approved_by: Mapped[uuid.UUID]
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    model_versions: Mapped[dict[str, str]] = mapped_column(JSON)


class OutboxEventModel(Base):
    """Outbox-Pattern (Kapitel 11.3): wird in derselben Transaktion wie
    Approval geschrieben, danach von einem separaten Worker verarbeitet und
    ueber Redis Streams verteilt (siehe infrastructure/events)."""

    __tablename__ = "outbox_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str]
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="pending")
    retry_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccessGrantModel(Base):
    """Vertretungszugriff, UC-09. Wird von infrastructure/security/rbac.py
    geprueft, bevor Zugriff auf einen fremden patient_ref gewaehrt wird."""

    __tablename__ = "access_grants"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID]
    patient_ref: Mapped[str] = mapped_column(String, index=True)
    granted_by: Mapped[uuid.UUID]
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
