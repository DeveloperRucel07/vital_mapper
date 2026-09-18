from __future__ import annotations

import time
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, status

from vital_mapper.config import settings

_jwks: dict[str, Any] | None = None
_jwks_expiry = 0.0


def _auth_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _load_jwks(force: bool = False) -> dict[str, Any]:
    global _jwks, _jwks_expiry
    now = time.monotonic()
    if not force and _jwks is not None and now < _jwks_expiry:
        return _jwks
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(settings.keycloak_jwks_url)
            response.raise_for_status()
            value = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=503, detail="Der Anmeldedienst ist momentan nicht erreichbar."
        ) from exc
    if not isinstance(value, dict) or not isinstance(value.get("keys"), list):
        raise HTTPException(
            status_code=503,
            detail="Der Anmeldedienst hat ungültige Schlüsseldaten geliefert.",
        )
    _jwks = value
    _jwks_expiry = now + 300
    return value


async def _key_for_token(token: str) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise _auth_error("Ungültiger Signaturalgorithmus im Token.")
    except jwt.PyJWTError as exc:
        raise _auth_error("Ungültiges Token.") from exc
    for force in (False, True):
        jwks = await _load_jwks(force)
        key = next(
            (
                item
                for item in jwks["keys"]
                if isinstance(item, dict) and item.get("kid") == header["kid"]
            ),
            None,
        )
        if key is not None:
            return key, header
    raise _auth_error("Der Signaturschlüssel des Tokens ist unbekannt.")


async def verify_access_token(token: str) -> dict[str, Any]:
    key, _header = await _key_for_token(token)
    try:
        payload = jwt.decode(
            token,
            jwt.PyJWK.from_dict(key).key,
            algorithms=["RS256"],
            audience=settings.keycloak_api_audience,
            issuer=settings.keycloak_issuer,
        )
    except jwt.PyJWTError as exc:
        raise _auth_error("Ungültiges oder abgelaufenes Zugriffstoken.") from exc
    if payload.get("typ") != "Bearer" or payload.get("azp") != settings.keycloak_client_id:
        raise _auth_error("Das Zugriffstoken wurde nicht für diesen Client ausgestellt.")
    if not isinstance(payload.get("sub"), str):
        raise _auth_error("Das Zugriffstoken enthält keine Benutzeridentität.")
    return dict(payload)


async def verify_id_token(token: str, nonce: str) -> dict[str, Any]:
    key, _header = await _key_for_token(token)
    try:
        payload = jwt.decode(
            token,
            jwt.PyJWK.from_dict(key).key,
            algorithms=["RS256"],
            audience=settings.keycloak_client_id,
            issuer=settings.keycloak_issuer,
        )
    except jwt.PyJWTError as exc:
        raise _auth_error("Ungültiges ID-Token.") from exc
    if payload.get("nonce") != nonce or payload.get("azp") != settings.keycloak_client_id:
        raise _auth_error("Die OIDC-Sicherheitsbindung ist ungültig.")
    if not isinstance(payload.get("sub"), str):
        raise _auth_error("Das ID-Token enthält keine Benutzeridentität.")
    return dict(payload)


def client_roles(payload: dict[str, Any]) -> frozenset[str]:
    access = payload.get("resource_access")
    api_access = access.get(settings.keycloak_api_audience) if isinstance(access, dict) else None
    roles = api_access.get("roles") if isinstance(api_access, dict) else None
    return (
        frozenset(role for role in roles if isinstance(role, str))
        if isinstance(roles, list)
        else frozenset()
    )


def client_scopes(payload: dict[str, Any]) -> frozenset[str]:
    value = payload.get("scope")
    return frozenset(value.split()) if isinstance(value, str) else frozenset()
