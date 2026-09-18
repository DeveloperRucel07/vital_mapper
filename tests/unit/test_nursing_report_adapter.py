from datetime import UTC, datetime
from typing import Any

import pytest

from vital_mapper.domain.value_objects import ClinicalExtraction, Schmerz, Vitalparameter
from vital_mapper.infrastructure.interop.nursing_report_adapter import (
    GatewayNursingReportAdapter,
)


class FakeGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any], str]] = []

    async def request(
        self, path: str, payload: dict[str, Any], access_token: str
    ) -> dict[str, Any]:
        self.calls.append((path, payload, access_token))
        if path == "/interop/v1/patient/encounters":
            return {
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Encounter",
                            "id": "encounter-1",
                            "status": "in-progress",
                            "subject": {"reference": "Patient/patient-1"},
                        }
                    }
                ]
            }
        if path == "/interop/v1/patient/nursing-reports":
            return {"resourceType": "Composition", "id": "report-1"}
        return {"resourceType": "Observation", "id": f"observation-{len(self.calls)}"}


@pytest.mark.asyncio
async def test_adapter_maps_grounded_values_to_monitoring_contract() -> None:
    gateway = FakeGateway()
    extraction = ClinicalExtraction(
        vitalparameter=Vitalparameter(
            blutdruck_systolisch=150,
            blutdruck_diastolisch=80,
            puls=85,
            temperatur=37.0,
            spo2=100,
        ),
        schmerz=Schmerz(intensitaet_nrs=3),
    )
    recorded_at = datetime(2026, 9, 18, 15, 10, tzinfo=UTC)

    result = await GatewayNursingReportAdapter(gateway).submit_nursing_report(
        "patient-1", "Synthetischer Bericht.", extraction, recorded_at, "token-1"
    )

    assert isinstance(result["report"], dict)
    assert len(result["vital_measurements"]) == 5
    assert [call[0] for call in gateway.calls] == [
        "/interop/v1/patient/encounters",
        "/interop/v1/patient/nursing-reports",
        "/interop/v1/patient/vital-measurements",
        "/interop/v1/patient/vital-measurements",
        "/interop/v1/patient/vital-measurements",
        "/interop/v1/patient/vital-measurements",
        "/interop/v1/patient/vital-measurements",
    ]
    measurement_payloads = [call[1] for call in gateway.calls[2:]]
    assert measurement_payloads[0]["measurementType"] == "blood-pressure"
    assert measurement_payloads[0]["systolic"] == 150.0
    assert measurement_payloads[0]["diastolic"] == 80.0
    assert measurement_payloads[1]["measurementType"] == "heart-rate"
    assert measurement_payloads[2]["measurementType"] == "temperature"
    assert measurement_payloads[3]["measurementType"] == "oxygen-saturation"
    assert measurement_payloads[4]["measurementType"] == "pain"
    assert all(payload["encounterId"] == "encounter-1" for payload in measurement_payloads)
    assert all(payload["measuredAt"] == recorded_at.isoformat() for payload in measurement_payloads)
