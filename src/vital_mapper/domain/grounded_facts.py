"""Deterministische Erkennung explizit genannter klinischer Fakten (F-08/F-10).

Diese Erkennung ergänzt ausschließlich Werte, die in klaren, domänenspezifischen
Formulierungen im geprüften Transkript vorkommen. Sie ist kein Ersatz für die
LLM-Extraktion und darf keine plausiblen, aber nicht genannten Werte erzeugen.
"""

from __future__ import annotations

import re

from vital_mapper.domain.value_objects import (
    ClinicalExtraction,
    Fluessigkeit,
    Vitalparameter,
)

_INTEGER = r"\d{1,5}"
_DECIMAL = r"\d{1,3}(?:[,.]\d{1,2})?"
_NUMBER_WORDS = {
    "tausend": 1000,
    "eintausend": 1000,
}


def _number(value: str) -> int:
    """Konvertiert eine explizit genannte ganze Zahl."""

    normalized = value.lower().strip()
    if normalized in _NUMBER_WORDS:
        return _NUMBER_WORDS[normalized]
    return int(normalized.replace(".", ""))


def _decimal(value: str) -> float:
    """Konvertiert deutsche Dezimalschreibweise für Temperaturwerte."""

    return float(value.replace(",", "."))


def _search(pattern: str, transcript: str) -> re.Match[str] | None:
    return re.search(pattern, transcript, flags=re.IGNORECASE)


def apply_explicit_grounded_facts(
    extraction: ClinicalExtraction, transcript: str
) -> ClinicalExtraction:
    """Ergänzt sicher erkennbare Fakten aus dem geprüften Transkript.

    Unterstützt die in UC-02/F-10 vorgesehenen Formulierungen für Blutdruck,
    Puls, Temperatur und Flüssigkeitsmenge. Bereits genannte Fakten werden mit
    der deterministischen Transkriptinformation überschrieben, damit eine
    widersprüchliche LLM-Antwort nicht als klinischer Wert weitergegeben wird.
    Alle anderen Felder bleiben unverändert.
    """

    vital_updates: dict[str, int | float] = {}
    blood_pressure = _search(
        rf"\bblutdruck\b\s*(?:von|ist|beträgt)?\s*({_INTEGER})\s*(?:zu|/|auf)\s*({_INTEGER})",
        transcript,
    )
    if blood_pressure:
        vital_updates["blutdruck_systolisch"] = _number(blood_pressure.group(1))
        vital_updates["blutdruck_diastolisch"] = _number(blood_pressure.group(2))

    pulse = _search(
        rf"\b(?:puls|herzfrequenz)\b\s*(?:von|ist|beträgt)?\s*({_INTEGER})",
        transcript,
    )
    if pulse:
        vital_updates["puls"] = _number(pulse.group(1))

    temperature = _search(rf"\btemperatur\b\s*(?:von|ist|beträgt)?\s*({_DECIMAL})", transcript)
    if temperature:
        vital_updates["temperatur"] = _decimal(temperature.group(1))

    result = extraction
    if vital_updates:
        vital = result.vitalparameter or Vitalparameter(
            blutdruck_systolisch=None,
            blutdruck_diastolisch=None,
            puls=None,
            temperatur=None,
            spo2=None,
        )
        result = result.model_copy(
            update={"vitalparameter": vital.model_copy(update=vital_updates)}
        )

    fluid = _search(
        r"\b(?P<amount>\d{1,5}|tausend|eintausend)\s*"
        r"(?:milliliter|ml)\b(?:\s+(?P<drink>[A-Za-zÄÖÜäöüß-]+))?",
        transcript,
    )
    if fluid:
        fluid_updates: dict[str, int | str] = {
            "menge_ml": _number(fluid.group("amount")),
        }
        if fluid.group("drink"):
            fluid_updates["getraenk"] = fluid.group("drink")
        existing_fluid = result.fluessigkeit or Fluessigkeit()
        result = result.model_copy(
            update={"fluessigkeit": existing_fluid.model_copy(update=fluid_updates)}
        )

    return result
