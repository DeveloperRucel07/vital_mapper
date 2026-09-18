from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
    audio_storage_path: str = "/var/lib/vital-mapper/audio"
    max_audio_bytes: int = 25_000_000

    audio_retention_days: int = 30


# Pydantic Settings befuellt diese Pflichtfelder zur Laufzeit aus env/.env.
settings = Settings()  # type: ignore[call-arg]
