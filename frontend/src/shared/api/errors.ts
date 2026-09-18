export type ApiErrorKind =
  | "authentication"
  | "authorization"
  | "validation"
  | "not_found"
  | "conflict"
  | "server"
  | "network"
  | "unknown";

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status?: number;

  constructor(kind: ApiErrorKind, message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
  }
}

export function errorForStatus(status: number, detail?: string): ApiError {
  if (status === 401) return new ApiError("authentication", "Die Sitzung ist abgelaufen.", status);
  if (status === 403) return new ApiError("authorization", detail ?? "Für diese Aktion fehlt die Berechtigung.", status);
  if (status === 404) return new ApiError("not_found", detail ?? "Die angeforderte Ressource wurde nicht gefunden.", status);
  if (status === 409) return new ApiError("conflict", detail ?? "Die Änderung steht im Konflikt mit dem aktuellen Stand.", status);
  if (status === 422) return new ApiError("validation", detail ?? "Die Eingaben konnten nicht validiert werden.", status);
  if (status >= 500) return new ApiError("server", "Der Server ist momentan nicht verfügbar.", status);
  return new ApiError("unknown", detail ?? "Die Anfrage konnte nicht verarbeitet werden.", status);
}
