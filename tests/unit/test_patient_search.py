import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from vital_mapper.domain.entities import UserRole
from vital_mapper.infrastructure.security.auth import CurrentUser
from vital_mapper.interfaces.api.routers import interop


def test_patient_search_requires_at_least_one_criterion() -> None:
    with pytest.raises(ValidationError):
        interop.PatientSearchRequest()


def test_patient_search_normalizes_name_filters() -> None:
    request = interop.PatientSearchRequest(given=" Anna ", family=" Muster ")

    assert request.given == "Anna"
    assert request.family == "Muster"
    assert request.birthdate is None


@pytest.mark.asyncio
async def test_patient_search_forwards_given_family_and_birthdate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object], str]] = []

    class FakeGateway:
        async def request(
            self, path: str, payload: dict[str, object], access_token: str
        ) -> dict[str, object]:
            calls.append((path, payload, access_token))
            return {"resourceType": "Bundle", "entry": []}

    monkeypatch.setattr(interop, "HttpInteropGatewayAdapter", FakeGateway)
    access_token = uuid.uuid4().hex
    user = CurrentUser(uuid.uuid4(), UserRole.PFLEGEFACHKRAFT, access_token=access_token)
    request = interop.PatientSearchRequest(
        given="Anna", family="Muster", birthdate=date(1985, 4, 12)
    )

    result = await interop.search_patients(request, user)

    assert result == {"resourceType": "Bundle", "entry": []}
    assert calls == [
        (
            "/interop/v1/patients/search",
            {"family": "Muster", "given": "Anna", "birthdate": "1985-04-12"},
            access_token,
        )
    ]
