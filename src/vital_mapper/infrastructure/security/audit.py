"""Manipulationserkennbare Audit-Persistenz fuer Patientenzugriffe (F-33/NF-06)."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vital_mapper.config import settings
from vital_mapper.domain.exceptions import AuditIntegrityError
from vital_mapper.infrastructure.persistence.models import AuditEventModel, AuditLedgerStateModel

logger = structlog.get_logger("audit")


@dataclass(frozen=True)
class AuditEntry:
    """Minimaler, kliniktextfreier Datensatz zur Integritaetspruefung (NF-06)."""

    occurred_at: datetime
    actor_id: str
    patient_ref: str
    action: str
    purpose: str
    previous_hash: str
    entry_hash: str


def _audit_key() -> bytes:
    """Nutzt in Entwicklung einen klar markierten Fallback, nie in Produktion."""

    return (settings.audit_hmac_key or settings.jwt_secret_key).encode("utf-8")


def calculate_entry_hash(
    occurred_at: datetime,
    actor_id: str,
    patient_ref: str,
    action: str,
    purpose: str,
    previous_hash: str,
) -> str:
    """Berechnet den kanonischen HMAC eines verketteten Audit-Eintrags (NF-06)."""

    canonical = json.dumps(
        {
            "action": action,
            "actor_id": actor_id,
            "occurred_at": occurred_at.astimezone(UTC).isoformat(),
            "patient_ref": patient_ref,
            "previous_hash": previous_hash,
            "purpose": purpose,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hmac.new(_audit_key(), canonical, hashlib.sha256).hexdigest()


def is_valid_audit_chain(entries: list[AuditEntry], last_hash: str) -> bool:
    """Prueft Reihenfolge, HMAC und Endanker einer Audit-Kette (NF-06)."""

    previous_hash = ""
    for entry in entries:
        expected_hash = calculate_entry_hash(
            entry.occurred_at,
            entry.actor_id,
            entry.patient_ref,
            entry.action,
            entry.purpose,
            previous_hash,
        )
        if entry.previous_hash != previous_hash or not hmac.compare_digest(
            entry.entry_hash, expected_hash
        ):
            return False
        previous_hash = entry.entry_hash
    return hmac.compare_digest(previous_hash, last_hash)


async def verify_audit_ledger(session: AsyncSession) -> None:
    """Blockiert den Start bei einer festgestellten Audit-Manipulation (NF-06)."""

    models = (
        await session.scalars(select(AuditEventModel).order_by(AuditEventModel.sequence.asc()))
    ).all()
    state = await session.get(AuditLedgerStateModel, 1)
    entries = [
        AuditEntry(
            occurred_at=model.occurred_at,
            actor_id=model.actor_id,
            patient_ref=model.patient_ref,
            action=model.action,
            purpose=model.purpose,
            previous_hash=model.previous_hash,
            entry_hash=model.entry_hash,
        )
        for model in models
    ]
    last_hash = state.last_hash if state is not None else ""
    if not is_valid_audit_chain(entries, last_hash):
        raise AuditIntegrityError("Die Audit-Integritaetspruefung ist fehlgeschlagen.")


async def log_access(session: AsyncSession, user_id: str, patient_ref: str, action: str) -> None:
    """Persistiert einen Zugriff atomar in einer HMAC-verketteten Audit-Kette."""

    occurred_at = datetime.now(UTC)
    try:
        state = await session.scalar(
            select(AuditLedgerStateModel).where(AuditLedgerStateModel.id == 1).with_for_update()
        )
        if state is None:
            state = AuditLedgerStateModel(id=1, last_hash="")
            session.add(state)
            await session.flush()

        previous_hash = state.last_hash
        entry_hash = calculate_entry_hash(
            occurred_at, user_id, patient_ref, action, action, previous_hash
        )
        session.add(
            AuditEventModel(
                occurred_at=occurred_at,
                actor_id=user_id,
                patient_ref=patient_ref,
                action=action,
                purpose=action,
                previous_hash=previous_hash,
                entry_hash=entry_hash,
            )
        )
        state.last_hash = entry_hash
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    logger.info("patient_data_access", user_id=user_id, patient_ref=patient_ref, action=action)
