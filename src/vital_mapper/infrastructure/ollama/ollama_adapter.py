from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from vital_mapper.application.ports.extraction_port import ExtractionPort
from vital_mapper.domain.exceptions import UngroundedExtractionError
from vital_mapper.domain.grounded_facts import apply_explicit_grounded_facts
from vital_mapper.domain.value_objects import ClinicalExtraction

_GERMAN_NUMBER_WORDS = {
    "null": "0",
    "eins": "1",
    "ein": "1",
    "eine": "1",
    "zwei": "2",
    "drei": "3",
    "vier": "4",
    "fuenf": "5",
    "fünf": "5",
    "sechs": "6",
    "sieben": "7",
    "acht": "8",
    "neun": "9",
    "zehn": "10",
    "elf": "11",
    "zwoelf": "12",
    "tausend": "1000",
    "eintausend": "1000",
    "zwölf": "12",
}


def _normalize_number_words(text: str) -> str:
    """Ersetzt ausgeschriebene deutsche Zahlwoerter (0-12) durch Ziffern.
    Notwendig, weil Pflegekraefte Schmerzwerte haeufig als Wort sagen
    ('vier von zehn' statt '4') und Whisper das entsprechend als Text
    transkribiert - ohne diese Normalisierung wuerde der Grounding-Check
    korrekte Extraktionen faelschlich als 'nicht im Transkript belegt'
    zurueckweisen (siehe tests/unit/test_grounding_check.py)."""

    def replace(match: re.Match[str]) -> str:
        return _GERMAN_NUMBER_WORDS.get(match.group(0), match.group(0))

    return re.sub(r"[a-zA-Zäöüß]+", replace, text)


EXTRACTION_SYSTEM_PROMPT = (
    "Du extrahierst ausschliesslich Informationen, die woertlich oder "
    "sinngemaess im folgenden Pflegebericht-Transkript vorkommen. Erfinde "
    "oder ergaenze KEINE Werte. Erzeuge ein Unterobjekt immer dann, wenn "
    "mindestens ein zugehoeriger Fakt genannt wurde; gib nicht das gesamte "
    "Schema mit null zurueck, wenn Werte vorhanden sind. "
    "Ordne Formulierungen wie 'Blutdruck 150 zu 80' oder '150/80' den "
    "Feldern blutdruck_systolisch=150 und blutdruck_diastolisch=80 zu. "
    "Ordne 'Puls 80' dem Feld puls und 'Temperatur 37,0' dem Feld "
    "temperatur zu. Ordne 'tausend Milliliter Wasser' den Feldern "
    "fluessigkeit.menge_ml=1000 und fluessigkeit.getraenk='Wasser' zu. "
    "Wenn eine Information fehlt, lasse das Feld leer und trage den "
    "Feldpfad in 'unsichere_felder' ein."
)


def _numeric_value_is_grounded(value: str, transcript: str) -> bool:
    """Vergleicht Zahlen unabhängig von Dezimaltrennzeichen und Leerzeichen."""

    try:
        expected = Decimal(value)
    except InvalidOperation:
        return False

    numeric_tokens = re.findall(r"(?<!\d)\d+(?:\s*[,\.]\s*\d+)?(?!\d)", transcript)
    for token in numeric_tokens:
        try:
            candidate = Decimal(re.sub(r"\s+", "", token).replace(",", "."))
        except InvalidOperation:
            continue
        if candidate == expected:
            return True
    return False


def _sanitize_ungrounded_numeric_values(
    extraction: ClinicalExtraction, transcript: str
) -> ClinicalExtraction:
    """Entfernt ungroundete Zahlen und markiert sie als unsicher (F-08/F-15).

    Ein einzelner Halluzinationswert darf die gesamte klinische Extraktion
    nicht in einen HTTP-500-Fehler verwandeln. Der Wert wird deshalb verworfen;
    der nachgelagerte Grounding-Check bleibt als Sicherheitsnetz aktiv.
    """

    normalized = _normalize_number_words(re.sub(r"\s+", " ", transcript.lower()))
    numeric_fields: tuple[tuple[str, str], ...] = (
        ("vitalparameter", "blutdruck_systolisch"),
        ("vitalparameter", "blutdruck_diastolisch"),
        ("vitalparameter", "puls"),
        ("vitalparameter", "temperatur"),
        ("vitalparameter", "spo2"),
        ("schmerz", "intensitaet_nrs"),
        ("fluessigkeit", "menge_ml"),
        ("ernaehrung", "anteil_prozent"),
    )
    parent_updates: dict[str, Any] = {}
    uncertain_fields = list(extraction.unsichere_felder)

    for parent_name, field_name in numeric_fields:
        parent = parent_updates.get(parent_name, getattr(extraction, parent_name))
        if parent is None:
            continue
        value = getattr(parent, field_name)
        if value is None or _numeric_value_is_grounded(str(value), normalized):
            continue
        parent_updates[parent_name] = parent.model_copy(update={field_name: None})
        path = f"{parent_name}.{field_name}"
        if path not in uncertain_fields:
            uncertain_fields.append(path)

    if not parent_updates and uncertain_fields == extraction.unsichere_felder:
        return extraction
    return extraction.model_copy(update={**parent_updates, "unsichere_felder": uncertain_fields})


class OllamaExtractionAdapter(ExtractionPort):
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url
        self._model = model

    async def extract(self, transcript_text: str) -> tuple[ClinicalExtraction, str]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=60.0) as client:
            response = await client.post(
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": transcript_text},
                    ],
                    "format": ClinicalExtraction.model_json_schema(),
                    "options": {"temperature": 0},
                    "stream": False,
                },
            )
            response.raise_for_status()
            content = response.json()["message"]["content"]

        extraction = ClinicalExtraction.model_validate_json(content)
        extraction = apply_explicit_grounded_facts(extraction, transcript_text)
        extraction = _sanitize_ungrounded_numeric_values(extraction, transcript_text)
        self._assert_grounded(extraction, transcript_text)
        return extraction, self._model

    @staticmethod
    def _assert_grounded(extraction: ClinicalExtraction, transcript_text: str) -> None:
        """MVP-Grounding-Check: numerische Werte muessen im Transkript
        auftauchen. Fuer Freitextfelder (z. B. Lokalisation, Beschreibung)
        empfiehlt sich spaeter ein Embedding-basierter Aehnlichkeitscheck
        statt reinem String-Match - siehe Anforderungsdokument Kapitel 12
        (offener Punkt: Deidentifikations-/Extraktions-Qualitaetssicherung)."""
        normalized = re.sub(r"\s+", " ", transcript_text.lower())
        normalized = _normalize_number_words(normalized)
        numeric_values: list[str] = []

        if extraction.vitalparameter:
            for value in (
                extraction.vitalparameter.blutdruck_systolisch,
                extraction.vitalparameter.blutdruck_diastolisch,
                extraction.vitalparameter.puls,
                extraction.vitalparameter.temperatur,
            ):
                if value is not None:
                    numeric_values.append(str(value))

        if extraction.schmerz and extraction.schmerz.intensitaet_nrs is not None:
            numeric_values.append(str(extraction.schmerz.intensitaet_nrs))

        if extraction.fluessigkeit and extraction.fluessigkeit.menge_ml is not None:
            numeric_values.append(str(extraction.fluessigkeit.menge_ml))

        if extraction.ernaehrung and extraction.ernaehrung.anteil_prozent is not None:
            numeric_values.append(str(extraction.ernaehrung.anteil_prozent))

        for extracted_value in numeric_values:
            if not _numeric_value_is_grounded(extracted_value, normalized):
                raise UngroundedExtractionError(
                    f"Wert '{extracted_value}' wurde extrahiert, kommt aber nicht im "
                    "Transkript vor."
                )
