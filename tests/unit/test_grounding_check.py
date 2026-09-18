import pytest

from vital_mapper.domain.exceptions import UngroundedExtractionError
from vital_mapper.domain.grounded_facts import apply_explicit_grounded_facts
from vital_mapper.domain.value_objects import (
    ClinicalExtraction,
    Fluessigkeit,
    Schmerz,
    Vitalparameter,
)
from vital_mapper.infrastructure.ollama.ollama_adapter import (
    OllamaExtractionAdapter,
    _sanitize_ungrounded_numeric_values,
)


def test_grounded_extraction_passes(sample_transcript: str) -> None:
    extraction = ClinicalExtraction(
        vitalparameter=Vitalparameter(blutdruck_systolisch=135, blutdruck_diastolisch=80, puls=76),
        schmerz=Schmerz(intensitaet_nrs=4),
    )
    OllamaExtractionAdapter._assert_grounded(extraction, sample_transcript)  # darf nicht werfen


def test_ungrounded_value_is_rejected(sample_transcript: str) -> None:
    extraction = ClinicalExtraction(vitalparameter=Vitalparameter(puls=999))
    with pytest.raises(UngroundedExtractionError):
        OllamaExtractionAdapter._assert_grounded(extraction, sample_transcript)


def test_spelled_out_pain_score_is_grounded() -> None:
    """Regressionstest: Pflegekraefte sagen Schmerzwerte oft als Wort
    ('vier von zehn'), nicht als Ziffer - das darf der Grounding-Check nicht
    faelschlich als 'erfunden' ablehnen."""
    transcript = "Patient klagt ueber Schmerzen, Staerke vier von zehn."
    extraction = ClinicalExtraction(schmerz=Schmerz(intensitaet_nrs=4))
    OllamaExtractionAdapter._assert_grounded(extraction, transcript)  # darf nicht werfen


def test_explicit_german_clinical_facts_are_completed() -> None:
    transcript = (
        "Blutdruck von 150 zu 80, Puls 80, Temperatur 37,0. "
        "Sie hat tausend Milliliter Wasser getrunken."
    )
    completed = apply_explicit_grounded_facts(ClinicalExtraction(), transcript)

    assert completed.vitalparameter == Vitalparameter(
        blutdruck_systolisch=150,
        blutdruck_diastolisch=80,
        puls=80,
        temperatur=37.0,
    )
    assert completed.fluessigkeit == Fluessigkeit(menge_ml=1000, getraenk="Wasser")
    OllamaExtractionAdapter._assert_grounded(completed, transcript)


def test_explicit_facts_do_not_invent_missing_categories() -> None:
    completed = apply_explicit_grounded_facts(
        ClinicalExtraction(), "Der Zustand ist heute stabil und die Patientin ist müde."
    )

    assert completed.vitalparameter is None
    assert completed.fluessigkeit is None


def test_decimal_temperature_grounding_accepts_german_spacing() -> None:
    extraction = ClinicalExtraction(
        vitalparameter=Vitalparameter(
            blutdruck_systolisch=None,
            blutdruck_diastolisch=None,
            puls=None,
            temperatur=37.0,
            spo2=None,
        )
    )

    OllamaExtractionAdapter._assert_grounded(extraction, "Temperatur 37 , 0 Grad.")


def test_ungrounded_numeric_value_is_marked_uncertain_instead_of_aborting() -> None:
    extraction = ClinicalExtraction(
        vitalparameter=Vitalparameter(
            blutdruck_systolisch=None,
            blutdruck_diastolisch=None,
            puls=85,
            temperatur=None,
            spo2=None,
        )
    )

    sanitized = _sanitize_ungrounded_numeric_values(extraction, "Der Zustand ist stabil.")

    assert sanitized.vitalparameter is not None
    assert sanitized.vitalparameter.puls is None
    assert "vitalparameter.puls" in sanitized.unsichere_felder
    OllamaExtractionAdapter._assert_grounded(sanitized, "Der Zustand ist stabil.")
