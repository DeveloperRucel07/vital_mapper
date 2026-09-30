import pytest
from pydantic import ValidationError

from vital_mapper.config import Settings


def _base_settings() -> dict[str, object]:
    return {
        "database_url": "postgresql+asyncpg://user:password@db/vitalmapper",
        "redis_url": "redis://redis:6379/0",
        "ollama_base_url": "http://ollama:11434",
        "whisper_base_url": "http://whisper:8001",
        "fhir_base_url": "http://fhir/fhir",
        "jwt_secret_key": "synthetic-jwt-secret",
        "audio_encryption_key": "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
    }


def test_development_allows_local_unencrypted_service_urls() -> None:
    settings = Settings(_env_file=None, **_base_settings())  # type: ignore[arg-type]

    assert settings.app_env == "development"


def test_production_rejects_unencrypted_transport() -> None:
    values = _base_settings()
    values["app_env"] = "production"

    with pytest.raises(ValidationError, match="Unsichere Produktionskonfiguration"):
        Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_production_accepts_secure_transport_configuration() -> None:
    values = _base_settings()
    values.update(
        {
            "app_env": "production",
            "database_url": "postgresql+asyncpg://user:password@db/vitalmapper?ssl=require",
            "redis_url": "rediss://redis:6379/0",
            "bff_redis_url": "rediss://redis:6379/1",
            "ollama_base_url": "https://ollama.internal",
            "whisper_base_url": "https://whisper.internal",
            "fhir_base_url": "https://fhir.internal/fhir",
            "app_origin": "https://vital-mapper.example.invalid",
            "interop_gateway_url": "https://interop.internal",
            "bff_cookie_secure": True,
            "legacy_auth_enabled": False,
            "clinical_data_encryption_key": ("MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE="),
        }
    )

    settings = Settings(_env_file=None, **values)  # type: ignore[arg-type]

    assert settings.app_env == "production"


def test_invalid_fernet_key_is_rejected_without_echoing_secret() -> None:
    values = _base_settings()
    values["audio_encryption_key"] = "not-a-fernet-key"

    with pytest.raises(ValidationError, match="Ungueltiger Fernet-Schluessel") as error:
        Settings(_env_file=None, **values)  # type: ignore[arg-type]

    assert "not-a-fernet-key" not in str(error.value)
