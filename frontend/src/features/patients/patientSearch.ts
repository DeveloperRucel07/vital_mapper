export interface PatientSearchCriteria {
  given: string;
  family: string;
  birthdate: string;
}

export type PatientSearchPayload = Partial<{
  given: string;
  family: string;
  birthdate: string;
}>;

export function buildPatientSearchPayload(criteria: PatientSearchCriteria): PatientSearchPayload {
  const payload: PatientSearchPayload = {};
  const given = criteria.given.trim();
  const family = criteria.family.trim();
  const birthdate = criteria.birthdate.trim();

  if (given) payload.given = given;
  if (family) payload.family = family;
  if (birthdate) payload.birthdate = birthdate;

  return payload;
}
