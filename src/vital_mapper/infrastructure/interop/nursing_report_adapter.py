from __future__ import annotations

from datetime import datetime
from typing import Any

from vital_mapper.application.ports.nursing_report_port import NursingReportPort
from vital_mapper.domain.value_objects import ClinicalExtraction
from vital_mapper.infrastructure.interop.gateway_adapter import (
    HttpInteropGatewayAdapter,
    InteropGatewayError,
)


class GatewayNursingReportAdapter(NursingReportPort):
    """Uebergibt freigegebene Dokumentation ausschliesslich ueber den Gateway (NF-30/F-20)."""

    def __init__(self, gateway: HttpInteropGatewayAdapter | None = None) -> None:
        self._gateway = gateway or HttpInteropGatewayAdapter()

    async def submit_nursing_report(
        self,
        patient_ref: str,
        report_text: str,
        extraction: ClinicalExtraction,
        recorded_at: datetime,
        access_token: str,
    ) -> dict[str, object]:
        if not access_token:
            raise InteropGatewayError(
                "Fuer die Monitoring-Uebergabe ist eine OIDC-Sitzung erforderlich."
            )
        if not report_text.strip() or len(report_text) > 4000:
            raise InteropGatewayError(
                "Der Pflegebericht muss zwischen 1 und 4000 Zeichen enthalten."
            )

        encounters = await self._gateway.request(
            "/interop/v1/patient/encounters", {"patientId": patient_ref}, access_token
        )
        encounter_id = _active_encounter_id(encounters, patient_ref)
        report_result = await self._gateway.request(
            "/interop/v1/patient/nursing-reports",
            {
                "patientId": patient_ref,
                "encounterId": encounter_id,
                "title": "Pflegebericht Vital Mapper",
                "text": report_text.strip(),
            },
            access_token,
        )
        vital_results: list[dict[str, Any]] = []
        for payload in _vital_measurement_payloads(
            patient_ref, encounter_id, extraction, recorded_at
        ):
            vital_results.append(
                await self._gateway.request(
                    "/interop/v1/patient/vital-measurements", payload, access_token
                )
            )
        return {"report": report_result, "vital_measurements": vital_results}


def _active_encounter_id(payload: dict[str, Any], patient_ref: str) -> str:
    entries = payload.get("entry")
    if not isinstance(entries, list):
        raise InteropGatewayError("Das Monitoring lieferte keinen Fallkontext.")
    for entry in entries:
        resource = entry.get("resource") if isinstance(entry, dict) else None
        if not isinstance(resource, dict):
            continue
        if resource.get("resourceType") != "Encounter":
            continue
        if resource.get("status") not in {"arrived", "triaged", "in-progress", "onleave"}:
            continue
        if (resource.get("subject") or {}).get("reference") != f"Patient/{patient_ref}":
            continue
        encounter_id = resource.get("id")
        if isinstance(encounter_id, str) and encounter_id:
            return encounter_id
    raise InteropGatewayError("Fuer den Patienten wurde kein aktiver Fall gefunden.")


def _vital_measurement_payloads(
    patient_ref: str,
    encounter_id: str,
    extraction: ClinicalExtraction,
    recorded_at: datetime,
) -> list[dict[str, Any]]:
    """Mappt nur erkannte Vitalwerte auf den Monitoring-Vertrag (F-08/F-20)."""
    vitalparameter = extraction.vitalparameter
    if vitalparameter is None:
        return []

    measured_at = recorded_at.isoformat()
    context = {
        "patientId": patient_ref,
        "encounterId": encounter_id,
        "measuredAt": measured_at,
    }
    payloads: list[dict[str, Any]] = []
    if (
        vitalparameter.blutdruck_systolisch is not None
        and vitalparameter.blutdruck_diastolisch is not None
    ):
        payloads.append(
            {
                **context,
                "measurementType": "blood-pressure",
                "systolic": float(vitalparameter.blutdruck_systolisch),
                "diastolic": float(vitalparameter.blutdruck_diastolisch),
            }
        )
    numeric_mappings = (
        ("puls", "heart-rate"),
        ("temperatur", "temperature"),
        ("spo2", "oxygen-saturation"),
    )
    for field_name, measurement_type in numeric_mappings:
        value = getattr(vitalparameter, field_name)
        if value is not None:
            payloads.append(
                {
                    **context,
                    "measurementType": measurement_type,
                    "value": float(value),
                }
            )

    pain = extraction.schmerz
    if pain is not None and pain.intensitaet_nrs is not None:
        payloads.append(
            {
                **context,
                "measurementType": "pain",
                "value": float(pain.intensitaet_nrs),
            }
        )
    return payloads
