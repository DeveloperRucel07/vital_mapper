from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from vital_mapper.config import settings
from vital_mapper.domain.entities import User, UserRole
from vital_mapper.infrastructure.security.keycloak import client_roles, verify_access_token
from vital_mapper.infrastructure.security.oidc_bff import (
    SESSION_COOKIE_NAME,
    OidcUnavailableError,
    load_session,
    oidc_configured,
)

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(
        self,
        id: uuid.UUID,
        role: UserRole,
        *,
        subject: str | None = None,
        claims: dict[str, Any] | None = None,
        access_token: str | None = None,
    ) -> None:
        self.id = id
        self.role = role
        self.subject = subject or str(id)
        self.claims = claims or {}
        self.access_token = access_token


def create_access_token(user: User) -> str:
    """Stellt ein kurzlebiges JWT fuer ein authentifiziertes Konto aus (F-30)."""
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.jwt_access_token_minutes)
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "type": "access",
        "iat": issued_at,
        "exp": expires_at,
    }
    return str(jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm))


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if oidc_configured():
        claims: dict[str, Any]
        delegated_token: str
        if credentials is not None and credentials.scheme.lower() == "bearer":
            delegated_token = credentials.credentials
            claims = await verify_access_token(delegated_token)
        else:
            session_id = request.cookies.get(SESSION_COOKIE_NAME)
            if not session_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Anmeldung erforderlich."
                )
            try:
                session = await load_session(session_id)
            except OidcUnavailableError as exc:
                raise HTTPException(
                    status_code=503, detail="Der Sitzungsdienst ist momentan nicht erreichbar."
                ) from exc
            token = session.get("token") if session else None
            access_token = token.get("access_token") if isinstance(token, dict) else None
            if not isinstance(access_token, str):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Die Sitzung ist abgelaufen."
                )
            delegated_token = access_token
            claims = await verify_access_token(delegated_token)
            expected_csrf = session.get("csrf_token") if session else None
            supplied_csrf = request.headers.get("X-CSRF-Token", "")
            if request.method not in {"GET", "HEAD", "OPTIONS"} and (
                request.headers.get("Origin") != settings.app_origin
                or not isinstance(expected_csrf, str)
                or not secrets.compare_digest(supplied_csrf, expected_csrf)
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Die Sicherheitsprüfung der Anfrage ist fehlgeschlagen.",
                )
        roles = client_roles(claims)
        if not roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Keine API-Rolle zugewiesen."
            )
        subject = claims["sub"]
        role = _domain_role(roles)
        return CurrentUser(
            uuid.uuid5(uuid.NAMESPACE_URL, f"keycloak:{subject}"),
            role,
            subject=subject,
            claims=claims,
            access_token=delegated_token,
        )

    if not settings.legacy_auth_enabled or credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Anmeldung erforderlich."
        )
    try:
        decoded_payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        payload = decoded_payload
        subject = payload.get("sub")
        legacy_role = payload.get("role")
        jwt_kind = payload.get("type")
        if not isinstance(subject, str) or not isinstance(legacy_role, str) or jwt_kind != "access":
            raise ValueError("Token-Claims fehlen")
        return CurrentUser(
            id=uuid.UUID(subject),
            role=UserRole(legacy_role),
            subject=subject,
            claims=payload,
            access_token=credentials.credentials,
        )
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Ungueltiges Token"
        ) from exc


def _domain_role(roles: frozenset[str]) -> UserRole:
    if "pflege_admin" in roles:
        return UserRole.ADMINISTRATOR
    if "pflege_write" in roles:
        return UserRole.PFLEGEFACHKRAFT
    if "pflege_read" in roles:
        return UserRole.PFLEGEFACHKRAFT
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Keine verwertbare API-Rolle zugewiesen."
    )
