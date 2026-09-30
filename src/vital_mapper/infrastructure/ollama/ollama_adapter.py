from __future__ import annotations

import re
import unicodedata
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


def _normalized_text(value: str) -> str:
    """Normalisiert Freitext fuer einen konservativen Faktenabgleich (F-08)."""

    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", without_accents)).strip()


def _text_value_is_grounded(value: str, transcript: str) -> bool:
    """Erlaubt Freitext nur, wenn er als zusammenhaengende Aussage vorkommt."""

    normalized_value = _normalized_text(value)
    normalized_transcript = _normalized_text(transcript)
    if not normalized_value:
        return False
    if f" {normalized_value} " in f" {normalized_transcript} ":
        return True

    def token_pattern(token: str) -> str:
        stem = re.sub(r"(?:ern|em|en|es|er|e)$", "", token)
        return re.escape(stem) + r"\w*" if len(stem) >= 4 else re.escape(token)

    pattern = (
        r"\b" + r"\s+".join(token_pattern(token) for token in normalized_value.split()) + r"\b"
    )
    return bool(re.search(pattern, normalized_transcript))


def _pain_value_is_grounded(value: bool, transcript: str) -> bool:
    """Prueft Schmerz- und explizite Schmerzverneinungen getrennt (F-08/F-09)."""

    normalized = _normalized_text(transcript)
    pain_is_negated = bool(
        re.search(r"\b(keine?|ohne|verneint) schmerzen?\b|\bschmerzfrei\b", normalized)
    )
    pain_is_mentioned = bool(re.search(r"\bschmerzen?\b|\bschmerzfrei\b", normalized))
    return pain_is_mentioned and (not pain_is_negated if value else pain_is_negated)


def _fall_value_is_grounded(value: bool, transcript: str) -> bool:
    """Prueft Sturzereignisse einschliesslich expliziter Verneinung (F-08)."""

    normalized = _normalized_text(transcript)
    fall_is_negated = bool(
        re.search(r"\b(kein|keine|ohne) sturz(?:ereignis)?\b|\bnicht gesturzt\b", normalized)
    )
    fall_is_mentioned = bool(re.search(r"\bsturz(?:ereignis)?\b|\bgesturzt\b", normalized))
    return fall_is_mentioned and (not fall_is_negated if value else fall_is_negated)


def _enum_value_is_grounded(path: str, value: str, transcript: str) -> bool:
    """Ordnet nur klar benannte Fachformulierungen den Enum-Werten zu (F-08)."""

    normalized = _normalized_text(transcript)
    patterns: dict[tuple[str, str], tuple[str, ...]] = {
        ("mobilitaet.status", "selbststaendig"): (r"\bselbststandig\b",),
        ("mobilitaet.status", "rollator"): (r"\brollator\b",),
        ("mobilitaet.status", "unterstuetzung"): (
            r"\bunterstutzung\b",
            r"\bmit hilfe\b",
            r"\bbenotigt hilfe\b",
            r"\bassistenz\b",
        ),
        ("mobilitaet.gangbild", "sicher"): (
            r"\b(?:gang|gangbild|mobilitat)\b.{0,30}\bsicher\b",
            r"\bsicher\b.{0,30}\b(?:gang|gangbild|mobilitat)\b",
        ),
        ("mobilitaet.gangbild", "unsicher"): (
            r"\b(?:gang|gangbild|mobilitat)\b.{0,30}\bunsicher\b",
            r"\bunsicher\b.{0,30}\b(?:gang|gangbild|mobilitat)\b",
        ),
        ("orientierung.status", "orientiert"): (r"\borientiert\b",),
        ("orientierung.status", "desorientiert"): (r"\bdesorientiert\b",),
        ("reaktion.typ", "verbesserung"): (
            r"\bverbesser(?:ung|t)\b",
            r"\bbesser\b",
        ),
        ("reaktion.typ", "verschlechterung"): (
            r"\bverschlechter(?:ung|t)\b",
            r"\bschlechter\b",
        ),
    }
    return any(re.search(pattern, normalized) for pattern in patterns.get((path, value), ()))


def _sanitize_ungrounded_values(
    extraction: ClinicalExtraction, transcript: str
) -> ClinicalExtraction:
    """Entfernt unbelegte Fakten und markiert sie als unsicher (F-08/F-15).

    Ein Halluzinationswert darf die gesamte klinische Extraktion nicht in einen
    HTTP-500-Fehler verwandeln. Er wird deshalb verworfen; der nachgelagerte
    Grounding-Check bleibt als nicht umgehbares Sicherheitsnetz aktiv.
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
    text_fields: tuple[tuple[str, str], ...] = (
        ("schmerz", "lokalisation"),
        ("fluessigkeit", "getraenk"),
        ("ernaehrung", "beschreibung"),
        ("ausscheidung", "urin"),
        ("ausscheidung", "stuhl"),
        ("sturz", "zeitpunkt"),
        ("sturz", "verletzung"),
        ("sturz", "bewusstsein"),
        ("intervention", "typ"),
        ("intervention", "beschreibung"),
        ("reaktion", "beschreibung"),
    )
    enum_fields: tuple[tuple[str, str], ...] = (
        ("mobilitaet", "status"),
        ("mobilitaet", "gangbild"),
        ("orientierung", "status"),
        ("reaktion", "typ"),
    )
    parent_updates: dict[str, Any] = {}
    uncertain_fields = list(extraction.unsichere_felder)

    def clear_field(parent_name: str, field_name: str) -> None:
        parent = parent_updates.get(parent_name, getattr(extraction, parent_name))
        if parent is None:
            return
        parent_updates[parent_name] = parent.model_copy(update={field_name: None})
        path = f"{parent_name}.{field_name}"
        if path not in uncertain_fields:
            uncertain_fields.append(path)

    for parent_name, field_name in numeric_fields:
        parent = parent_updates.get(parent_name, getattr(extraction, parent_name))
        if parent is None:
            continue
        value = getattr(parent, field_name)
        if value is None or _numeric_value_is_grounded(str(value), normalized):
            continue
        clear_field(parent_name, field_name)

    for parent_name, field_name in text_fields:
        parent = parent_updates.get(parent_name, getattr(extraction, parent_name))
        if parent is None:
            continue
        value = getattr(parent, field_name)
        if value is not None and not _text_value_is_grounded(value, transcript):
            clear_field(parent_name, field_name)

    if extraction.schmerz and extraction.schmerz.vorhanden is not None:
        if not _pain_value_is_grounded(extraction.schmerz.vorhanden, transcript):
            clear_field("schmerz", "vorhanden")

    if extraction.sturz and extraction.sturz.ereignis is not None:
        if not _fall_value_is_grounded(extraction.sturz.ereignis, transcript):
            clear_field("sturz", "ereignis")

    for parent_name, field_name in enum_fields:
        parent = parent_updates.get(parent_name, getattr(extraction, parent_name))
        if parent is None:
            continue
        value = getattr(parent, field_name)
        path = f"{parent_name}.{field_name}"
        if value is not None and not _enum_value_is_grounded(path, value, transcript):
            clear_field(parent_name, field_name)

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
        extraction = _sanitize_ungrounded_values(extraction, transcript_text)
        self._assert_grounded(extraction, transcript_text)
        return extraction, self._model

    @staticmethod
    def _assert_grounded(extraction: ClinicalExtraction, transcript_text: str) -> None:
        """Verwirft jede nicht im Transkript belegte Extraktion (F-08/F-15)."""
        normalized = re.sub(r"\s+", " ", transcript_text.lower())
        normalized = _normalize_number_words(normalized)
        checks: list[tuple[str, bool]] = []

        if extraction.vitalparameter:
            for path, value in (
                (
                    "vitalparameter.blutdruck_systolisch",
                    extraction.vitalparameter.blutdruck_systolisch,
                ),
                (
                    "vitalparameter.blutdruck_diastolisch",
                    extraction.vitalparameter.blutdruck_diastolisch,
                ),
                ("vitalparameter.puls", extraction.vitalparameter.puls),
                ("vitalparameter.temperatur", extraction.vitalparameter.temperatur),
                ("vitalparameter.spo2", extraction.vitalparameter.spo2),
            ):
                if value is not None:
                    checks.append((path, _numeric_value_is_grounded(str(value), normalized)))

        if extraction.schmerz and extraction.schmerz.intensitaet_nrs is not None:
            checks.append(
                (
                    "schmerz.intensitaet_nrs",
                    _numeric_value_is_grounded(str(extraction.schmerz.intensitaet_nrs), normalized),
                )
            )

        if extraction.fluessigkeit and extraction.fluessigkeit.menge_ml is not None:
            checks.append(
                (
                    "fluessigkeit.menge_ml",
                    _numeric_value_is_grounded(str(extraction.fluessigkeit.menge_ml), normalized),
                )
            )

        if extraction.ernaehrung and extraction.ernaehrung.anteil_prozent is not None:
            checks.append(
                (
                    "ernaehrung.anteil_prozent",
                    _numeric_value_is_grounded(
                        str(extraction.ernaehrung.anteil_prozent), normalized
                    ),
                )
            )

        text_checks: tuple[tuple[str, Any], ...] = (
            (
                "schmerz.lokalisation",
                extraction.schmerz.lokalisation if extraction.schmerz else None,
            ),
            (
                "fluessigkeit.getraenk",
                extraction.fluessigkeit.getraenk if extraction.fluessigkeit else None,
            ),
            (
                "ernaehrung.beschreibung",
                extraction.ernaehrung.beschreibung if extraction.ernaehrung else None,
            ),
            (
                "ausscheidung.urin",
                extraction.ausscheidung.urin if extraction.ausscheidung else None,
            ),
            (
                "ausscheidung.stuhl",
                extraction.ausscheidung.stuhl if extraction.ausscheidung else None,
            ),
            ("sturz.zeitpunkt", extraction.sturz.zeitpunkt if extraction.sturz else None),
            ("sturz.verletzung", extraction.sturz.verletzung if extraction.sturz else None),
            ("sturz.bewusstsein", extraction.sturz.bewusstsein if extraction.sturz else None),
            ("intervention.typ", extraction.intervention.typ if extraction.intervention else None),
            (
                "intervention.beschreibung",
                extraction.intervention.beschreibung if extraction.intervention else None,
            ),
            (
                "reaktion.beschreibung",
                extraction.reaktion.beschreibung if extraction.reaktion else None,
            ),
        )
        for path, value in text_checks:
            if value is not None:
                checks.append((path, _text_value_is_grounded(value, transcript_text)))

        if extraction.schmerz and extraction.schmerz.vorhanden is not None:
            checks.append(
                (
                    "schmerz.vorhanden",
                    _pain_value_is_grounded(extraction.schmerz.vorhanden, transcript_text),
                )
            )
        if extraction.sturz and extraction.sturz.ereignis is not None:
            checks.append(
                (
                    "sturz.ereignis",
                    _fall_value_is_grounded(extraction.sturz.ereignis, transcript_text),
                )
            )

        enum_checks: tuple[tuple[str, Any], ...] = (
            ("mobilitaet.status", extraction.mobilitaet.status if extraction.mobilitaet else None),
            (
                "mobilitaet.gangbild",
                extraction.mobilitaet.gangbild if extraction.mobilitaet else None,
            ),
            (
                "orientierung.status",
                extraction.orientierung.status if extraction.orientierung else None,
            ),
            ("reaktion.typ", extraction.reaktion.typ if extraction.reaktion else None),
        )
        for path, value in enum_checks:
            if value is not None:
                checks.append((path, _enum_value_is_grounded(path, value, transcript_text)))

        for path, is_grounded in checks:
            if not is_grounded:
                raise UngroundedExtractionError(
                    f"Feld '{path}' wurde extrahiert, ist aber nicht im Transkript belegt."
                )
