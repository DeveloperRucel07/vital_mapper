import {
  type ClinicalExtractionData,
  optionalBoolean,
  optionalNumber,
  optionalText,
} from "./clinicalExtraction";

type Props = {
  data: ClinicalExtractionData;
  onChange: (data: ClinicalExtractionData) => void;
};

const FIELD_LABELS: Record<string, string> = {
  "vitalparameter.blutdruck_systolisch": "Blutdruck systolisch",
  "vitalparameter.blutdruck_diastolisch": "Blutdruck diastolisch",
  "vitalparameter.puls": "Puls",
  "vitalparameter.temperatur": "Temperatur",
  "vitalparameter.spo2": "Sauerstoffsättigung",
  "schmerz.vorhanden": "Schmerz vorhanden",
  "schmerz.lokalisation": "Schmerzlokalisation",
  "schmerz.intensitaet_nrs": "Schmerzstärke",
  "fluessigkeit.menge_ml": "Trinkmenge",
  "fluessigkeit.getraenk": "Getränk",
  "ernaehrung.anteil_prozent": "Nahrungsanteil",
};

function InputField({ label, value, onChange, type = "text", suffix, step }: {
  label: string;
  value: string | number | null;
  onChange: (value: string) => void;
  type?: "text" | "number";
  suffix?: string;
  step?: string;
}) {
  return <label className="clinical-field"><span>{label}</span><div className="clinical-input-wrap"><input type={type} step={step} value={value ?? ""} onChange={(event) => onChange(event.target.value)} />{suffix && <small>{suffix}</small>}</div></label>;
}

function SelectField({ label, value, options, onChange }: {
  label: string;
  value: string;
  options: Array<[string, string]>;
  onChange: (value: string) => void;
}) {
  return <label className="clinical-field"><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}>{options.map(([optionValue, optionLabel]) => <option value={optionValue} key={optionValue}>{optionLabel}</option>)}</select></label>;
}

function booleanValue(value: boolean | null): string {
  return value === null ? "" : String(value);
}

export function ClinicalInformationForm({ data, onChange }: Props) {
  function update<K extends keyof ClinicalExtractionData>(section: K, values: ClinicalExtractionData[K]): void {
    onChange({ ...data, [section]: values });
  }

  return <div className="clinical-information-form">
    <p className="muted">Prüfen Sie die erkannten Angaben fachlich. Nicht genannte Informationen bleiben leer.</p>
    {data.unsichere_felder.length > 0 && <div className="clinical-uncertainty" role="status"><strong>Bitte besonders prüfen</strong><span>{data.unsichere_felder.map((field) => FIELD_LABELS[field] ?? "Weitere Angabe").join(" · ")}</span></div>}
    <div className="clinical-sections">
      <fieldset><legend>Vitalwerte</legend><div className="clinical-fields">
        <InputField label="Blutdruck systolisch" type="number" value={data.vitalparameter.blutdruck_systolisch} suffix="mmHg" onChange={(value) => update("vitalparameter", { ...data.vitalparameter, blutdruck_systolisch: optionalNumber(value) })} />
        <InputField label="Blutdruck diastolisch" type="number" value={data.vitalparameter.blutdruck_diastolisch} suffix="mmHg" onChange={(value) => update("vitalparameter", { ...data.vitalparameter, blutdruck_diastolisch: optionalNumber(value) })} />
        <InputField label="Puls" type="number" value={data.vitalparameter.puls} suffix="/min" onChange={(value) => update("vitalparameter", { ...data.vitalparameter, puls: optionalNumber(value) })} />
        <InputField label="Temperatur" type="number" step="0.1" value={data.vitalparameter.temperatur} suffix="°C" onChange={(value) => update("vitalparameter", { ...data.vitalparameter, temperatur: optionalNumber(value) })} />
        <InputField label="Sauerstoffsättigung" type="number" value={data.vitalparameter.spo2} suffix="%" onChange={(value) => update("vitalparameter", { ...data.vitalparameter, spo2: optionalNumber(value) })} />
      </div></fieldset>
      <fieldset><legend>Schmerz</legend><div className="clinical-fields">
        <SelectField label="Schmerz vorhanden" value={booleanValue(data.schmerz.vorhanden)} options={[["", "Nicht angegeben"], ["true", "Ja"], ["false", "Nein"]]} onChange={(value) => update("schmerz", { ...data.schmerz, vorhanden: optionalBoolean(value) })} />
        <InputField label="Lokalisation" value={data.schmerz.lokalisation} onChange={(value) => update("schmerz", { ...data.schmerz, lokalisation: optionalText(value) })} />
        <InputField label="Schmerzstärke" type="number" value={data.schmerz.intensitaet_nrs} suffix="NRS 0–10" onChange={(value) => update("schmerz", { ...data.schmerz, intensitaet_nrs: optionalNumber(value) })} />
      </div></fieldset>
      <fieldset><legend>Trinken und Ernährung</legend><div className="clinical-fields">
        <InputField label="Trinkmenge" type="number" value={data.fluessigkeit.menge_ml} suffix="ml" onChange={(value) => update("fluessigkeit", { ...data.fluessigkeit, menge_ml: optionalNumber(value) })} />
        <InputField label="Getränk" value={data.fluessigkeit.getraenk} onChange={(value) => update("fluessigkeit", { ...data.fluessigkeit, getraenk: optionalText(value) })} />
        <InputField label="Nahrungsanteil" type="number" value={data.ernaehrung.anteil_prozent} suffix="%" onChange={(value) => update("ernaehrung", { ...data.ernaehrung, anteil_prozent: optionalNumber(value) })} />
        <InputField label="Ernährung – Beschreibung" value={data.ernaehrung.beschreibung} onChange={(value) => update("ernaehrung", { ...data.ernaehrung, beschreibung: optionalText(value) })} />
      </div></fieldset>
      <fieldset><legend>Mobilität und Orientierung</legend><div className="clinical-fields">
        <SelectField label="Mobilität" value={data.mobilitaet.status ?? ""} options={[["", "Nicht angegeben"], ["selbststaendig", "Selbstständig"], ["rollator", "Mit Rollator"], ["unterstuetzung", "Mit Unterstützung"]]} onChange={(value) => update("mobilitaet", { ...data.mobilitaet, status: optionalText(value) })} />
        <SelectField label="Gangbild" value={data.mobilitaet.gangbild ?? ""} options={[["", "Nicht angegeben"], ["sicher", "Sicher"], ["unsicher", "Unsicher"]]} onChange={(value) => update("mobilitaet", { ...data.mobilitaet, gangbild: optionalText(value) })} />
        <SelectField label="Orientierung" value={data.orientierung.status ?? ""} options={[["", "Nicht angegeben"], ["orientiert", "Orientiert"], ["desorientiert", "Desorientiert"]]} onChange={(value) => update("orientierung", { status: optionalText(value) })} />
      </div></fieldset>
      <fieldset><legend>Ausscheidung</legend><div className="clinical-fields">
        <InputField label="Urin" value={data.ausscheidung.urin} onChange={(value) => update("ausscheidung", { ...data.ausscheidung, urin: optionalText(value) })} />
        <InputField label="Stuhl" value={data.ausscheidung.stuhl} onChange={(value) => update("ausscheidung", { ...data.ausscheidung, stuhl: optionalText(value) })} />
      </div></fieldset>
      <fieldset><legend>Sturzereignis</legend><div className="clinical-fields">
        <SelectField label="Sturzereignis" value={booleanValue(data.sturz.ereignis)} options={[["", "Nicht angegeben"], ["true", "Ja"], ["false", "Nein"]]} onChange={(value) => update("sturz", { ...data.sturz, ereignis: optionalBoolean(value) })} />
        <InputField label="Zeitpunkt" value={data.sturz.zeitpunkt} onChange={(value) => update("sturz", { ...data.sturz, zeitpunkt: optionalText(value) })} />
        <InputField label="Verletzung" value={data.sturz.verletzung} onChange={(value) => update("sturz", { ...data.sturz, verletzung: optionalText(value) })} />
        <InputField label="Bewusstseinslage" value={data.sturz.bewusstsein} onChange={(value) => update("sturz", { ...data.sturz, bewusstsein: optionalText(value) })} />
      </div></fieldset>
      <fieldset><legend>Maßnahme und Reaktion</legend><div className="clinical-fields">
        <InputField label="Maßnahme" value={data.intervention.typ} onChange={(value) => update("intervention", { ...data.intervention, typ: optionalText(value) })} />
        <InputField label="Maßnahme – Beschreibung" value={data.intervention.beschreibung} onChange={(value) => update("intervention", { ...data.intervention, beschreibung: optionalText(value) })} />
        <SelectField label="Reaktion" value={data.reaktion.typ ?? ""} options={[["", "Nicht angegeben"], ["verbesserung", "Verbesserung"], ["verschlechterung", "Verschlechterung"]]} onChange={(value) => update("reaktion", { ...data.reaktion, typ: optionalText(value) })} />
        <InputField label="Reaktion – Beschreibung" value={data.reaktion.beschreibung} onChange={(value) => update("reaktion", { ...data.reaktion, beschreibung: optionalText(value) })} />
      </div></fieldset>
    </div>
  </div>;
}
