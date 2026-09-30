export type OptionalText = string | null;
export type OptionalNumber = number | null;
export type OptionalBoolean = boolean | null;

export type ClinicalExtractionData = {
  vitalparameter: {
    blutdruck_systolisch: OptionalNumber;
    blutdruck_diastolisch: OptionalNumber;
    puls: OptionalNumber;
    temperatur: OptionalNumber;
    spo2: OptionalNumber;
  };
  schmerz: {
    vorhanden: OptionalBoolean;
    lokalisation: OptionalText;
    intensitaet_nrs: OptionalNumber;
  };
  fluessigkeit: { menge_ml: OptionalNumber; getraenk: OptionalText };
  ernaehrung: { anteil_prozent: OptionalNumber; beschreibung: OptionalText };
  mobilitaet: { status: OptionalText; gangbild: OptionalText };
  orientierung: { status: OptionalText };
  ausscheidung: { urin: OptionalText; stuhl: OptionalText };
  sturz: {
    ereignis: OptionalBoolean;
    zeitpunkt: OptionalText;
    verletzung: OptionalText;
    bewusstsein: OptionalText;
  };
  intervention: { typ: OptionalText; beschreibung: OptionalText };
  reaktion: { typ: OptionalText; beschreibung: OptionalText };
  unsichere_felder: string[];
};

type UnknownRecord = Record<string, unknown>;

function record(value: unknown): UnknownRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as UnknownRecord : {};
}

function text(value: unknown): OptionalText {
  return typeof value === "string" && value.trim() ? value : null;
}

function number(value: unknown): OptionalNumber {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function boolean(value: unknown): OptionalBoolean {
  return typeof value === "boolean" ? value : null;
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

export function normalizeClinicalExtraction(value: unknown): ClinicalExtractionData {
  const source = record(value);
  const vital = record(source.vitalparameter);
  const pain = record(source.schmerz);
  const fluid = record(source.fluessigkeit);
  const nutrition = record(source.ernaehrung);
  const mobility = record(source.mobilitaet);
  const orientation = record(source.orientierung);
  const elimination = record(source.ausscheidung);
  const fall = record(source.sturz);
  const intervention = record(source.intervention);
  const reaction = record(source.reaktion);

  return {
    vitalparameter: {
      blutdruck_systolisch: number(vital.blutdruck_systolisch),
      blutdruck_diastolisch: number(vital.blutdruck_diastolisch),
      puls: number(vital.puls),
      temperatur: number(vital.temperatur),
      spo2: number(vital.spo2),
    },
    schmerz: {
      vorhanden: boolean(pain.vorhanden),
      lokalisation: text(pain.lokalisation),
      intensitaet_nrs: number(pain.intensitaet_nrs),
    },
    fluessigkeit: { menge_ml: number(fluid.menge_ml), getraenk: text(fluid.getraenk) },
    ernaehrung: { anteil_prozent: number(nutrition.anteil_prozent), beschreibung: text(nutrition.beschreibung) },
    mobilitaet: { status: text(mobility.status), gangbild: text(mobility.gangbild) },
    orientierung: { status: text(orientation.status) },
    ausscheidung: { urin: text(elimination.urin), stuhl: text(elimination.stuhl) },
    sturz: {
      ereignis: boolean(fall.ereignis),
      zeitpunkt: text(fall.zeitpunkt),
      verletzung: text(fall.verletzung),
      bewusstsein: text(fall.bewusstsein),
    },
    intervention: { typ: text(intervention.typ), beschreibung: text(intervention.beschreibung) },
    reaktion: { typ: text(reaction.typ), beschreibung: text(reaction.beschreibung) },
    unsichere_felder: strings(source.unsichere_felder),
  };
}

export function optionalNumber(value: string): OptionalNumber {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function optionalText(value: string): OptionalText {
  return value.trim() ? value : null;
}

export function optionalBoolean(value: string): OptionalBoolean {
  if (value === "true") return true;
  if (value === "false") return false;
  return null;
}
