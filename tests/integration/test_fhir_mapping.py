from vital_mapper.domain.value_objects import ClinicalExtraction, Vitalparameter
from vital_mapper.infrastructure.fhir.hapi_fhir_adapter import HapiFhirAdapter


def test_blood_pressure_uses_correct_loinc_codes() -> None:
    data = ClinicalExtraction(
        vitalparameter=Vitalparameter(blutdruck_systolisch=135, blutdruck_diastolisch=80)
    )
    resources = HapiFhirAdapter._build_observations("patient-123", data)

    assert len(resources) == 1
    bp_resource = resources[0]
    assert bp_resource["code"]["coding"][0]["code"] == "85354-9"
    codes = {c["code"]["coding"][0]["code"] for c in bp_resource["component"]}
    assert codes == {"8480-6", "8462-4"}
