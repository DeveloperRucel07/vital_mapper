import type { ApiClient } from "../../shared/api/client";
import type { UserRole } from "../../shared/types/api";

export interface AuthUser {
  id: string;
  displayName: string;
  role: UserRole;
}

export interface AuthSession {
  authenticated: boolean;
  user?: { subject: string; displayName: string; role: UserRole };
  capabilities?: { canRead: boolean; canWrite: boolean; canDelete: boolean };
  csrfToken?: string;
}

interface LogoutResponse {
  logout_path: string | null;
}

export async function getSession(client: ApiClient): Promise<AuthSession> {
  const session = await client.get<AuthSession>("/auth/session");
  if (session.csrfToken) client.setCsrfToken(session.csrfToken);
  return session;
}

export async function logout(client: ApiClient): Promise<string | null> {
  const response = await client.post<LogoutResponse>("/auth/logout", {});
  client.setCsrfToken(null);
  return response.logout_path;
}

export function beginLogin(returnTo = "/"): void {
  window.location.assign(`/auth/login?return_to=${encodeURIComponent(returnTo)}`);
}
