from __future__ import annotations

from datetime import date
from typing import Any, Self

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from vital_mapper.domain.entities import UserRole
from vital_mapper.infrastructure.interop.gateway_adapter import (
    HttpInteropGatewayAdapter,
    InteropGatewayError,
)
from vital_mapper.infrastructure.security.auth import CurrentUser
from vital_mapper.infrastructure.security.rbac import require_role

router = APIRouter(prefix="/interop/v1", tags=["interoperability"])


class PatientSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: str | None = Field(default=None, min_length=1, max_length=100)
    given: str | None = Field(default=None, min_length=1, max_length=100)
    birthdate: date | None = None

    @field_validator("family", "given", mode="before")
    @classmethod
    def normalize_name_filter(cls, value: object) -> object:
        """Normalizes text filters and rejects whitespace-only values (F-01)."""
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def require_search_criteria(self) -> Self:
        """Requires at least one patient search criterion (F-01/F-31)."""
        if self.family is None and self.given is None and self.birthdate is None:
            raise ValueError("Mindestens ein Suchkriterium ist erforderlich.")
        return self


class PatientContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_ref: str = Field(pattern=r"^[A-Za-z0-9.-]{1,64}$")


async def _forward(path: str, payload: dict[str, Any], user: CurrentUser) -> dict[str, Any]:
    if not user.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="OIDC-Sitzung erforderlich."
        )
    try:
        return await HttpInteropGatewayAdapter().request(path, payload, user.access_token)
    except InteropGatewayError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/patients/search")
async def search_patients(
    body: PatientSearchRequest,
    user: CurrentUser = Depends(
        require_role(UserRole.PFLEGEFACHKRAFT, UserRole.SCHICHTLEITUNG, UserRole.ADMINISTRATOR)
    ),
) -> dict[str, Any]:
    """Reads the monitoring patient index through the gateway, never HAPI directly (F-30/F-31)."""
    return await _forward(
        "/interop/v1/patients/search", body.model_dump(mode="json", exclude_none=True), user
    )


@router.post("/patient/read")
async def read_patient(
    body: PatientContextRequest,
    user: CurrentUser = Depends(
        require_role(UserRole.PFLEGEFACHKRAFT, UserRole.SCHICHTLEITUNG, UserRole.ADMINISTRATOR)
    ),
) -> dict[str, Any]:
    return await _forward("/interop/v1/patient/read", {"patientId": body.patient_ref}, user)


@router.post("/patient/observations")
async def read_observations(
    body: PatientContextRequest,
    user: CurrentUser = Depends(
        require_role(UserRole.PFLEGEFACHKRAFT, UserRole.SCHICHTLEITUNG, UserRole.ADMINISTRATOR)
    ),
) -> dict[str, Any]:
    return await _forward("/interop/v1/patient/observations", {"patientId": body.patient_ref}, user)


@router.post("/patient/encounters")
async def read_encounters(
    body: PatientContextRequest,
    user: CurrentUser = Depends(
        require_role(UserRole.PFLEGEFACHKRAFT, UserRole.SCHICHTLEITUNG, UserRole.ADMINISTRATOR)
    ),
) -> dict[str, Any]:
    return await _forward("/interop/v1/patient/encounters", {"patientId": body.patient_ref}, user)
