import base64
import binascii
from typing import Self
from urllib.parse import parse_qs, urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str
    redis_url: str

    ollama_base_url: str
    ollama_model: str = "llama3.1:8b-instruct"

    whisper_base_url: str

    fhir_base_url: str
    fhir_auth_token: str = ""

    # OIDC/BFF integration. Tokens remain server-side in the encrypted session.
    keycloak_issuer: str = ""
    keycloak_jwks_url: str = ""
    keycloak_api_audience: str = "monitoring-pflege-api"
    keycloak_client_id: str = "vital-mapper-frontend"
    keycloak_client_secret: str = ""
    oidc_authorization_url: str = ""
    oidc_token_url: str = ""
    oidc_logout_url: str = ""
    app_origin: str = "http://localhost:3000"
    bff_redis_url: str = "redis://redis:6379/1"
    bff_session_encryption_key: str = ""
    bff_cookie_secure: bool = False
    interop_gateway_url: str = "http://interop-gateway:8000"
    interop_timeout_seconds: float = 10.0
    legacy_auth_enabled: bool = True

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 15
    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: str | None = None
    audio_encryption_key: str
    clinical_data_encryption_key: str = ""
    audio_storage_path: str = "/var/lib/vital-mapper/audio"
    max_audio_bytes: int = 25_000_000

    audio_retention_days: int = Field(default=30, ge=1)
    audio_retention_check_seconds: int = Field(default=3600, ge=60)

    @field_validator("audio_encryption_key", "clinical_data_encryption_key")
    @classmethod
    def validate_fernet_key(cls, value: str) -> str:
        """Akzeptiert nur URL-safe Base64-Schluessel mit 32 Byte Nutzlaenge."""

        if not value:
            return value
        try:
            decoded = base64.urlsafe_b64decode(value.encode("ascii"))
        except (binascii.Error, UnicodeEncodeError, ValueError) as exc:
            raise ValueError("Ungueltiger Fernet-Schluessel.") from exc
        if len(decoded) != 32:
            raise ValueError("Ungueltiger Fernet-Schluessel.")
        return value

    @model_validator(mode="after")
    def require_secure_production_transport(self) -> Self:
        """Verhindert unverschluesselte Produktionskonfigurationen (F-26)."""

        if self.app_env.lower() not in {"production", "prod"}:
            return self

        insecure: list[str] = []
        https_settings = {
            "OLLAMA_BASE_URL": self.ollama_base_url,
            "WHISPER_BASE_URL": self.whisper_base_url,
            "FHIR_BASE_URL": self.fhir_base_url,
            "KEYCLOAK_ISSUER": self.keycloak_issuer,
            "KEYCLOAK_JWKS_URL": self.keycloak_jwks_url,
            "OIDC_AUTHORIZATION_URL": self.oidc_authorization_url,
            "OIDC_TOKEN_URL": self.oidc_token_url,
            "OIDC_LOGOUT_URL": self.oidc_logout_url,
            "APP_ORIGIN": self.app_origin,
            "INTEROP_GATEWAY_URL": self.interop_gateway_url,
        }
        for name, value in https_settings.items():
            if value and not value.lower().startswith("https://"):
                insecure.append(name)
        if not self.redis_url.lower().startswith("rediss://"):
            insecure.append("REDIS_URL")
        if not self.bff_redis_url.lower().startswith("rediss://"):
            insecure.append("BFF_REDIS_URL")
        database_query = parse_qs(urlparse(self.database_url).query)
        ssl_mode = (database_query.get("ssl") or database_query.get("sslmode") or [""])[0]
        if ssl_mode.lower() not in {"require", "verify-ca", "verify-full", "true"}:
            insecure.append("DATABASE_URL")
        if not self.bff_cookie_secure:
            insecure.append("BFF_COOKIE_SECURE")
        if self.legacy_auth_enabled:
            insecure.append("LEGACY_AUTH_ENABLED")
        if not self.clinical_data_encryption_key:
            insecure.append("CLINICAL_DATA_ENCRYPTION_KEY")
        elif self.clinical_data_encryption_key == self.audio_encryption_key:
            insecure.append("CLINICAL_DATA_ENCRYPTION_KEY_KEY_SEPARATION")

        if insecure:
            names = ", ".join(sorted(set(insecure)))
            raise ValueError(f"Unsichere Produktionskonfiguration fuer: {names}")
        return self


# Pydantic Settings befuellt diese Pflichtfelder zur Laufzeit aus env/.env.
settings = Settings()  # type: ignore[call-arg]
