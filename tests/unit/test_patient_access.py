import uuid
from datetime import datetime
from typing import cast

import pytest
from fastapi import HTTPException

from vital_mapper.domain.entities import UserRole
from vital_mapper.infrastructure.persistence.repository import PostgresRepository
from vital_mapper.infrastructure.security.auth import CurrentUser
from vital_mapper.interfaces.api.routers import drafts


class FakeAccessRepository:
    def __init__(self, has_access: bool) -> None:
        self._has_access = has_access

    async def get_patient_ref_for_draft(self, draft_id: uuid.UUID) -> str:
        return "synthetic-patient-001"

    async def find_active_grant(
        self, user_id: str, patient_ref: str, now: datetime
    ) -> object | None:
        return object() if self._has_access else None


async def test_patient_access_is_allowed_with_active_grant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logged: list[tuple[str, str, str]] = []

    async def fake_log_access(user_id: str, patient_ref: str, action: str) -> None:
        logged.append((user_id, patient_ref, action))

    monkeypatch.setattr(drafts, "log_access", fake_log_access)
    user = CurrentUser(uuid.uuid4(), UserRole.PFLEGEFACHKRAFT)
    repository = cast(PostgresRepository, FakeAccessRepository(has_access=True))

    patient_ref = await drafts._assert_patient_access(repository, uuid.uuid4(), user, "read")

    assert patient_ref == "synthetic-patient-001"
    assert logged == [(str(user.id), patient_ref, "read")]


async def test_patient_access_is_rejected_without_active_grant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_log_access(user_id: str, patient_ref: str, action: str) -> None:
        return None

    monkeypatch.setattr(drafts, "log_access", fake_log_access)
    user = CurrentUser(uuid.uuid4(), UserRole.PFLEGEFACHKRAFT)
    repository = cast(PostgresRepository, FakeAccessRepository(has_access=False))

    with pytest.raises(HTTPException) as error:
        await drafts._assert_patient_access(repository, uuid.uuid4(), user, "read")

    assert error.value.status_code == 403
