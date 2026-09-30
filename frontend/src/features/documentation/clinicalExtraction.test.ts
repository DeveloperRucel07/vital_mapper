import { describe, expect, it } from "vitest";
import { normalizeClinicalExtraction } from "./clinicalExtraction";

describe("normalizeClinicalExtraction", () => {
  it("maps API data to nursing-friendly editable fields without exposing JSON", () => {
    const data = normalizeClinicalExtraction({
      vitalparameter: { puls: 76, temperatur: 37.2 },
      schmerz: { vorhanden: true, intensitaet_nrs: 4 },
      unsichere_felder: ["schmerz.lokalisation"],
    });

    expect(data.vitalparameter.puls).toBe(76);
    expect(data.vitalparameter.temperatur).toBe(37.2);
    expect(data.schmerz.vorhanden).toBe(true);
    expect(data.schmerz.lokalisation).toBeNull();
    expect(data.unsichere_felder).toEqual(["schmerz.lokalisation"]);
  });
});
