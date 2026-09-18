from __future__ import annotations

from typing import Any

from vital_mapper.application.ports.fhir_port import FhirPort
from vital_mapper.domain.value_objects import ClinicalExtraction

LOINC = "http://loinc.org"
VITAL_SIGNS_CATEGORY = {
    "coding": [
        {
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "vital-signs",
        }
    ]
}


class HapiFhirAdapter(FhirPort):
    """Quarantined legacy adapter; direct HAPI access is forbidden (NF-30)."""

    def __init__(self, base_url: str, auth_token: str) -> None:
        del base_url, auth_token
        raise RuntimeError(
            "Direkter HAPI-FHIR-Zugriff ist deaktiviert. "
            "Verwenden Sie den Interoperabilitäts-Gateway."
        )

    async def submit_observation_bundle(
        self, patient_ref: str, data: ClinicalExtraction
    ) -> list[str]:
        del patient_ref, data
        raise RuntimeError(
            "Klinische Persistenz muss über den Interoperabilitäts-Gateway erfolgen."
        )

    async def submit_provenance(
        self, target_resource_ids: list[str], agent_id: str, meta: dict[str, Any]
    ) -> str:
        del target_resource_ids, agent_id, meta
        raise RuntimeError("Provenance muss über den Interoperabilitäts-Gateway erfolgen.")

    @staticmethod
    def _build_observations(patient_ref: str, data: ClinicalExtraction) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        subject = {"reference": f"Patient/{patient_ref}"}

        if data.vitalparameter:
            v = data.vitalparameter
            if v.blutdruck_systolisch is not None and v.blutdruck_diastolisch is not None:
                resources.append(
                    {
                        "resourceType": "Observation",
                        "status": "final",
                        "category": [VITAL_SIGNS_CATEGORY],
                        "code": {"coding": [{"system": LOINC, "code": "85354-9"}]},
                        "subject": subject,
                        "component": [
                            {
                                "code": {"coding": [{"system": LOINC, "code": "8480-6"}]},
                                "valueQuantity": {
                                    "value": v.blutdruck_systolisch,
                                    "unit": "mmHg",
                                },
                            },
                            {
                                "code": {"coding": [{"system": LOINC, "code": "8462-4"}]},
                                "valueQuantity": {
                                    "value": v.blutdruck_diastolisch,
                                    "unit": "mmHg",
                                },
                            },
                        ],
                    }
                )
            if v.puls is not None:
                resources.append(_simple_observation(subject, "8867-4", v.puls, "/min"))
            if v.temperatur is not None:
                resources.append(_simple_observation(subject, "8310-5", v.temperatur, "Cel"))
            if v.spo2 is not None:
                resources.append(_simple_observation(subject, "2708-6", v.spo2, "%"))

        if data.schmerz and data.schmerz.intensitaet_nrs is not None:
            resources.append(
                _simple_observation(subject, "72514-3", data.schmerz.intensitaet_nrs, "{score}")
            )

        return resources


def _simple_observation(
    subject: dict[str, str], code: str, value: float, unit: str
) -> dict[str, Any]:
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [VITAL_SIGNS_CATEGORY],
        "code": {"coding": [{"system": LOINC, "code": code}]},
        "subject": subject,
        "valueQuantity": {"value": value, "unit": unit},
    }
