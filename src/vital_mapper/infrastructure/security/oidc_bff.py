from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Response, status
from redis.asyncio import Redis

from vital_mapper.config import settings

SESSION_COOKIE_NAME = (
    "__Host-vital_mapper_session" if settings.bff_cookie_secure else "vital_mapper_session"
)
LOGIN_COOKIE_NAME = (
    "__Host-vital_mapper_login" if settings.bff_cookie_secure else "vital_mapper_login"
)
SESSION_IDLE_SECONDS = 1800
SESSION_ABSOLUTE_SECONDS = 28800


class OidcUnavailableError(RuntimeError):
    """Raised when the server-side OIDC session store is unavailable (NF-30)."""


def _redis() -> Redis:
    return Redis.from_url(
        settings.bff_redis_url,
        socket_connect_timeout=2,
        socket_timeout=2,
        decode_responses=False,
    )


def _cipher() -> Fernet:
    if not settings.bff_session_encryption_key:
        raise OidcUnavailableError("BFF session encryption is not configured.")
    try:
        return Fernet(settings.bff_session_encryption_key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise OidcUnavailableError("BFF session encryption is invalid.") from exc


def _key(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"vital-mapper:{prefix}:{digest}"


async def _write(prefix: str, value: str, payload: dict[str, Any], ttl: int) -> None:
    encoded = _cipher().encrypt(json.dumps(payload, separators=(",", ":")).encode())
    try:
        await _redis().setex(_key(prefix, value), ttl, encoded)
    except Exception as exc:  # redis exposes several connection exception types
        raise OidcUnavailableError("BFF session store is unavailable.") from exc


async def _read(prefix: str, value: str, *, delete: bool = False) -> dict[str, Any] | None:
    client = _redis()
    try:
        raw = await (
            client.getdel(_key(prefix, value)) if delete else client.get(_key(prefix, value))
        )
    except Exception as exc:
        raise OidcUnavailableError("BFF session store is unavailable.") from exc
    if not isinstance(raw, bytes):
        return None
    try:
        decoded = json.loads(_cipher().decrypt(raw))
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError):
        return None
    return decoded if isinstance(decoded, dict) else None


def safe_return_to(value: str | None) -> str:
    candidate = value or "/"
    parsed = urlparse(candidate)
    if (
        not candidate.startswith("/")
        or candidate.startswith("//")
        or parsed.scheme
        or parsed.netloc
    ):
        return "/"
    return candidate[:512]


async def create_login_flow(return_to: str, browser_binding: str) -> tuple[str, str, str]:
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    await _write(
        "flow",
        state,
        {
            "nonce": nonce,
            "verifier": verifier,
            "return_to": safe_return_to(return_to),
            "browser_binding": browser_binding,
        },
        300,
    )
    return state, nonce, verifier


async def consume_login_flow(state: str) -> dict[str, Any] | None:
    return await _read("flow", state, delete=True)


async def create_logout_flow(id_token_hint: str | None, post_logout_redirect_uri: str) -> str:
    """Stores provider logout data server-side and returns only a one-time code (NF-30)."""
    code = secrets.token_urlsafe(32)
    await _write(
        "logout",
        code,
        {
            "id_token_hint": id_token_hint,
            "post_logout_redirect_uri": post_logout_redirect_uri,
        },
        120,
    )
    return code


async def consume_logout_flow(code: str) -> dict[str, Any] | None:
    """Consumes a one-time provider logout code without exposing tokens to the browser."""
    return await _read("logout", code, delete=True)


async def create_session(token: dict[str, Any]) -> tuple[str, str]:
    now = int(time.time())
    session_id = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    await _write(
        "session",
        session_id,
        {
            "created_at": now,
            "absolute_expires_at": now + SESSION_ABSOLUTE_SECONDS,
            "csrf_token": csrf_token,
            "token": token,
        },
        SESSION_IDLE_SECONDS,
    )
    return session_id, csrf_token


async def load_session(session_id: str) -> dict[str, Any] | None:
    payload = await _read("session", session_id)
    if payload is None:
        return None
    now = int(time.time())
    absolute_expiry = payload.get("absolute_expires_at")
    if not isinstance(absolute_expiry, int) or absolute_expiry <= now:
        await delete_session(session_id)
        return None
    token = payload.get("token")
    if not isinstance(token, dict):
        await delete_session(session_id)
        return None
    obtained_at = token.get("obtained_at", payload.get("created_at", now))
    expires_in = token.get("expires_in", 0)
    if not isinstance(obtained_at, int) or not isinstance(expires_in, int):
        await delete_session(session_id)
        return None
    if obtained_at + expires_in <= now + 30:
        refreshed = await _refresh_token(token)
        if refreshed is None:
            await delete_session(session_id)
            return None
        payload["token"] = refreshed
    ttl = min(SESSION_IDLE_SECONDS, absolute_expiry - now)
    await _write("session", session_id, payload, ttl)
    return payload


async def delete_session(session_id: str) -> None:
    try:
        await _redis().delete(_key("session", session_id))
    except Exception as exc:
        raise OidcUnavailableError("BFF session store is unavailable.") from exc


async def _refresh_token(token: dict[str, Any]) -> dict[str, Any] | None:
    refresh_token = token.get("refresh_token")
    if not isinstance(refresh_token, str) or not settings.keycloak_client_secret:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.oidc_token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.keycloak_client_id,
                    "client_secret": settings.keycloak_client_secret,
                    "refresh_token": refresh_token,
                },
            )
            response.raise_for_status()
            refreshed = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(refreshed, dict) or not isinstance(refreshed.get("access_token"), str):
        return None
    refreshed.setdefault("refresh_token", refresh_token)
    refreshed["obtained_at"] = int(time.time())
    return refreshed


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        secure=settings.bff_cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        LOGIN_COOKIE_NAME,
        secure=settings.bff_cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        secure=settings.bff_cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )


def oidc_configured() -> bool:
    return all(
        (
            settings.keycloak_issuer,
            settings.keycloak_jwks_url,
            settings.keycloak_client_id,
            settings.keycloak_client_secret,
            settings.oidc_authorization_url,
            settings.oidc_token_url,
            settings.bff_session_encryption_key,
        )
    )


async def exchange_code(code: str, verifier: str, redirect_uri: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.oidc_token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.keycloak_client_id,
                    "client_secret": settings.keycloak_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": verifier,
                },
            )
            response.raise_for_status()
            token = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OIDC-Anmeldung konnte nicht abgeschlossen werden.",
        ) from exc
    if not isinstance(token, dict) or not isinstance(token.get("access_token"), str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OIDC-Anmeldung lieferte kein Zugriffstoken.",
        )
    token.setdefault("obtained_at", int(time.time()))
    return token


def authorization_url(state: str, nonce: str, verifier: str, redirect_uri: str) -> str:
    query = urlencode(
        {
            "response_type": "code",
            "client_id": settings.keycloak_client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid profile email patient:read",
            "state": state,
            "nonce": nonce,
            "code_challenge": pkce_challenge(verifier),
            "code_challenge_method": "S256",
            "prompt": "login",
        }
    )
    return f"{settings.oidc_authorization_url}?{query}"
