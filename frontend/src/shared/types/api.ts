export type UserRole =
  | "pflegefachkraft"
  | "schichtleitung"
  | "administrator"
  | "qualitaetsverantwortlicher"
  | "datenschutzbeauftragter";

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
}

export interface UserResponse {
  id: string;
  username: string;
  role: UserRole;
  active: boolean;
}

export interface ApprovalResponse {
  id: string;
  draft_id: string;
  approved_at: string;
}
