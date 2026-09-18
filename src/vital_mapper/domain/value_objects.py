from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Vitalparameter(BaseModel):
    blutdruck_systolisch: int | None = Field(None, description="mmHg")
    blutdruck_diastolisch: int | None = Field(None, description="mmHg")
    puls: int | None = Field(None, description="Schlaege/min")
    temperatur: float | None = Field(None, description="Grad Celsius")
    spo2: int | None = Field(None, description="Prozent")


class Schmerz(BaseModel):
    vorhanden: bool | None = None
    lokalisation: str | None = None
    intensitaet_nrs: int | None = Field(None, ge=0, le=10)


class Fluessigkeit(BaseModel):
    menge_ml: int | None = None
    getraenk: str | None = None


class Ernaehrung(BaseModel):
    anteil_prozent: int | None = None
    beschreibung: str | None = None


class Mobilitaet(BaseModel):
    status: Literal["selbststaendig", "rollator", "unterstuetzung"] | None = None
    gangbild: Literal["sicher", "unsicher"] | None = None


class Orientierung(BaseModel):
    status: Literal["orientiert", "desorientiert"] | None = None


class Ausscheidung(BaseModel):
    urin: str | None = None
    stuhl: str | None = None


class Sturz(BaseModel):
    ereignis: bool | None = None
    zeitpunkt: str | None = None
    verletzung: str | None = None
    bewusstsein: str | None = None


class Intervention(BaseModel):
    typ: str | None = None
    beschreibung: str | None = None


class Reaktion(BaseModel):
    typ: Literal["verbesserung", "verschlechterung"] | None = None
    beschreibung: str | None = None


class ClinicalExtraction(BaseModel):
    vitalparameter: Vitalparameter | None = None
    schmerz: Schmerz | None = None
    fluessigkeit: Fluessigkeit | None = None
    ernaehrung: Ernaehrung | None = None
    mobilitaet: Mobilitaet | None = None
    orientierung: Orientierung | None = None
    ausscheidung: Ausscheidung | None = None
    sturz: Sturz | None = None
    intervention: Intervention | None = None
    reaktion: Reaktion | None = None
    unsichere_felder: list[str] = Field(
        default_factory=list,
        description=(
            "Feldpfade, die das Modell nicht sicher aus dem Transkript ableiten "
            "konnte (F-15) - werden der Pflegefachkraft zur Pruefung markiert."
        ),
    )
