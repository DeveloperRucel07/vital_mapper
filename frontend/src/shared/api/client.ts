import { ApiError, errorForStatus } from "./errors";

const DEFAULT_BASE_URL = "";
// Klinische Extraktion kann beim ersten Ollama-Aufruf das Modell laden und
// mehrere zehn Sekunden dauern. Das Frontend darf die laufende Verarbeitung
// nicht vor dem Backend-/Proxy-Timeout abbrechen.
const REQUEST_TIMEOUT_MS = 420_000;

export class ApiClient {
  private readonly baseUrl: string;
  private csrfToken: string | null = null;

  constructor(baseUrl = import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  setCsrfToken(token: string | null): void {
    this.csrfToken = token;
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, { method: "POST", body: JSON.stringify(body) });
  }

  async postFormData<T>(path: string, body: FormData): Promise<T> {
    return this.request<T>(path, { method: "POST", body });
  }

  async patch<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, { method: "PATCH", body: JSON.stringify(body) });
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "GET" });
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    const headers = new Headers(init.headers);
    if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
    headers.set("Accept", "application/json");
    if (this.csrfToken && init.method && init.method !== "GET") headers.set("X-CSRF-Token", this.csrfToken);

    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        ...init,
        headers,
        credentials: "include",
        signal: controller.signal,
      });
      if (!response.ok) {
        let detail: string | undefined;
        try {
          const payload = (await response.json()) as { detail?: unknown };
          detail = formatErrorDetail(payload.detail);
        } catch {
          // The status-specific fallback below remains safe if the response has no JSON body.
        }
        throw errorForStatus(response.status, detail);
      }
      if (response.status === 204) return undefined as T;
      return (await response.json()) as T;
    } catch (error: unknown) {
      if (error instanceof ApiError) throw error;
      if (error instanceof DOMException && error.name === "AbortError") {
        throw new ApiError("network", "Die Anfrage hat zu lange gedauert.");
      }
      throw new ApiError("network", "Der Dienst ist nicht erreichbar.");
    } finally {
      window.clearTimeout(timeout);
    }
  }
}

function formatErrorDetail(detail: unknown): string | undefined {
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail)) return undefined;
  const messages = detail.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const value = item as { msg?: unknown; loc?: unknown[] };
    if (typeof value.msg !== "string") return [];
    const location = Array.isArray(value.loc) ? value.loc.filter((part) => typeof part === "string" || typeof part === "number").join(".") : "";
    return [location ? `${location}: ${value.msg}` : value.msg];
  });
  return messages.length > 0 ? messages.join("; ") : undefined;
}

export const apiClient = new ApiClient();
