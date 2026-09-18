from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from fastapi import Depends, HTTPException, status

from vital_mapper.domain.entities import UserRole
from vital_mapper.domain.exceptions import AccessDeniedError
from vital_mapper.infrastructure.security.auth import CurrentUser, get_current_user


def require_role(*allowed_roles: UserRole) -> Callable[[CurrentUser], CurrentUser]:
    def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Rolle nicht berechtigt.")
        return user

    return _dependency


class AccessGrantLookup(Protocol):
    async def find_active_grant(
        self, user_id: str, patient_ref: str, now: datetime
    ) -> object | None: ...


async def check_patient_access(
    user_id: str, patient_ref: str, access_grant_repo: AccessGrantLookup
) -> None:
    """Prueft aktiven Vertretungszugriff. TODO: Anbindung an die reguläre
    Zuweisung von Pflegekraft zu Patient, sobald diese Quelle feststeht
    (siehe Anforderungsdokument Kapitel 12, offener Punkt Berechtigungen)."""
    grant = await access_grant_repo.find_active_grant(user_id, patient_ref, datetime.now(UTC))
    if grant is None:
        raise AccessDeniedError(f"Kein aktiver Zugriff auf Patient {patient_ref}.")
