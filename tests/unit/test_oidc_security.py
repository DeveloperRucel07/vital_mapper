from urllib.parse import parse_qs, urlparse

from vital_mapper.infrastructure.security.keycloak import client_roles
from vital_mapper.infrastructure.security.oidc_bff import authorization_url, safe_return_to


def test_return_to_rejects_external_redirects() -> None:
    assert safe_return_to("https://evil.example/") == "/"
    assert safe_return_to("//evil.example/") == "/"
    assert safe_return_to("/patients") == "/patients"


def test_keycloak_roles_are_read_from_api_audience(monkeypatch) -> None:
    from vital_mapper.config import settings

    monkeypatch.setattr(settings, "keycloak_api_audience", "monitoring-pflege-api")
    claims = {
        "resource_access": {
            "monitoring-pflege-api": {"roles": ["pflege_read", "unexpected"]},
            "other-api": {"roles": ["pflege_admin"]},
        }
    }
    assert client_roles(claims) == frozenset({"pflege_read", "unexpected"})


def test_login_requires_fresh_identity_provider_authentication(monkeypatch) -> None:
    from vital_mapper.config import settings

    monkeypatch.setattr(settings, "oidc_authorization_url", "https://issuer.example/auth")
    monkeypatch.setattr(settings, "keycloak_client_id", "vital-mapper-frontend")
    query = parse_qs(
        urlparse(authorization_url("state", "nonce", "verifier", "http://app/callback")).query
    )

    assert query["prompt"] == ["login"]
