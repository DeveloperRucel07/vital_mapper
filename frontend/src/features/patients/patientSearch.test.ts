import { describe, expect, it } from "vitest";
import { buildPatientSearchPayload } from "./patientSearch";

describe("patient search payload", () => {
  it("sends every populated criterion and trims text filters", () => {
    expect(buildPatientSearchPayload({
      given: " Anna ",
      family: " Muster ",
      birthdate: "1985-04-12",
    })).toEqual({ given: "Anna", family: "Muster", birthdate: "1985-04-12" });
  });

  it("omits empty criteria so single-field searches stay supported", () => {
    expect(buildPatientSearchPayload({ given: "", family: "Muster", birthdate: "" }))
      .toEqual({ family: "Muster" });
    expect(buildPatientSearchPayload({ given: "", family: "", birthdate: "1970-01-01" }))
      .toEqual({ birthdate: "1970-01-01" });
  });
});
