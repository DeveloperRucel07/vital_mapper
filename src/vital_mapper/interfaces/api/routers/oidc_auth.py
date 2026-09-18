from __future__ import annotations

import base64
import hashlib
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from vital_mapper.config import settings
from vital_mapper.infrastructure.security.keycloak import (
    client_roles,
    verify_access_token,
    verify_id_token,
)
from vital_mapper.infrastructure.security.oidc_bff import (
    LOGIN_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    OidcUnavailableError,
    authorization_url,
    clear_auth_cookies,
    consume_login_flow,
    consume_logout_flow,
    create_login_flow,
    create_logout_flow,
    create_session,
    delete_session,
    exchange_code,
    load_session,
    oidc_configured,
    safe_return_to,
    set_session_cookie,
)

router = APIRouter(prefix="/auth", tags=["oidc-auth"])


def _not_configured() -> HTTPException:
    return HTTPException(status_code=503, detail="OIDC ist nicht konfiguriert.")


def _no_store(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return response


def _redirect_uri() -> str:
    """Return the allow-listed OIDC callback URI (NF-30)."""
    return settings.app_origin.rstrip("/") + "/auth/callback"


@router.get("/login")
async def login(request: Request, return_to: str = "/") -> RedirectResponse:
    """Starts Authorization Code + PKCE; browser tokens are never returned (NF-30)."""
    if not oidc_configured():
        raise _not_configured()
    binding = secrets.token_urlsafe(32)
    try:
        state, nonce, verifier = await create_login_flow(safe_return_to(return_to), binding)
    except OidcUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail="Der Sitzungsdienst ist momentan nicht erreichbar."
        ) from exc
    redirect_uri = _redirect_uri()
    response = RedirectResponse(
        authorization_url(state, nonce, verifier, redirect_uri), status_code=303
    )
    response.set_cookie(
        LOGIN_COOKIE_NAME,
        binding,
        secure=settings.bff_cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=300,
    )
    return _no_store(response)  # type: ignore[return-value]


@router.get("/callback")
async def callback(
    request: Request, code: str | None = None, state: str | None = None
) -> RedirectResponse:
    if not oidc_configured():
        raise _not_configured()
    if not code or not state:
        raise HTTPException(status_code=400, detail="OIDC-Rückgabe ist unvollständig.")
    try:
        flow = await consume_login_flow(state)
    except OidcUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail="Der Sitzungsdienst ist momentan nicht erreichbar."
        ) from exc
    binding = request.cookies.get(LOGIN_COOKIE_NAME)
    if (
        not flow
        or not isinstance(binding, str)
        or not secrets.compare_digest(binding, str(flow.get("browser_binding", "")))
    ):
        raise HTTPException(status_code=400, detail="Die OIDC-Sicherheitsbindung ist ungültig.")
    redirect_uri = _redirect_uri()
    token = await exchange_code(code, str(flow["verifier"]), redirect_uri)
    access_claims = await verify_access_token(str(token["access_token"]))
    id_token = token.get("id_token")
    if not isinstance(id_token, str):
        raise HTTPException(status_code=502, detail="OIDC-Anmeldung lieferte kein ID-Token.")
    id_claims = await verify_id_token(id_token, str(flow["nonce"]))
    at_hash = id_claims.get("at_hash")
    digest = hashlib.sha256(str(token["access_token"]).encode("ascii")).digest()[:16]
    expected_at_hash = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    if not isinstance(at_hash, str) or not secrets.compare_digest(at_hash, expected_at_hash):
        raise HTTPException(status_code=401, detail="Die OIDC-Tokenbindung ist ungültig.")
    if id_claims.get("sub") != access_claims.get("sub"):
        raise HTTPException(status_code=401, detail="Die OIDC-Identität stimmt nicht überein.")
    try:
        session_id, _csrf = await create_session(token)
    except OidcUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail="Der Sitzungsdienst ist momentan nicht erreichbar."
        ) from exc
    response = RedirectResponse(safe_return_to(str(flow.get("return_to", "/"))), status_code=303)
    response.delete_cookie(
        LOGIN_COOKIE_NAME,
        secure=settings.bff_cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )
    set_session_cookie(response, session_id)
    return _no_store(response)  # type: ignore[return-value]


@router.get("/session")
async def session(request: Request) -> JSONResponse:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return _no_store(JSONResponse({"authenticated": False}, status_code=200))  # type: ignore[return-value]
    try:
        session_data = await load_session(session_id)
    except OidcUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail="Der Sitzungsdienst ist momentan nicht erreichbar."
        ) from exc
    if session_data is None:
        return _no_store(JSONResponse({"authenticated": False}, status_code=200))  # type: ignore[return-value]
    token = session_data.get("token") if session_data else None
    access_token = token.get("access_token") if isinstance(token, dict) else None
    if not isinstance(access_token, str):
        return _no_store(JSONResponse({"authenticated": False}, status_code=200))  # type: ignore[return-value]
    claims = await verify_access_token(access_token)
    roles = client_roles(claims)
    role = "administrator" if "pflege_admin" in roles else "pflegefachkraft"
    response = JSONResponse(
        {
            "authenticated": True,
            "user": {
                "subject": claims["sub"],
                "displayName": str(
                    claims.get("name") or claims.get("preferred_username") or "Angemeldet"
                )[:200],
                "role": role,
            },
            "capabilities": {
                "canRead": not roles.isdisjoint(
                    {"pflege_read", "pflege_write", "pflege_delete", "pflege_admin"}
                ),
                "canWrite": not roles.isdisjoint({"pflege_write", "pflege_admin"}),
                "canDelete": not roles.isdisjoint({"pflege_delete", "pflege_admin"}),
            },
            "csrfToken": session_data.get("csrf_token"),
        }
    )
    return _no_store(response)  # type: ignore[return-value]


@router.post("/logout")
async def logout(request: Request, x_csrf_token: str = Header(default="")) -> JSONResponse:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        response = JSONResponse({"logout_path": None})
        clear_auth_cookies(response)
        return _no_store(response)  # type: ignore[return-value]
    session_data = await load_session(session_id)
    expected = session_data.get("csrf_token") if session_data else None
    if (
        request.headers.get("Origin") != settings.app_origin
        or not isinstance(expected, str)
        or not secrets.compare_digest(x_csrf_token, expected)
    ):
        raise HTTPException(status_code=403, detail="Ungültige Sicherheitsprüfung.")
    logout_path: str | None = None
    if session_data is not None:
        token = session_data.get("token")
        id_token_hint = token.get("id_token") if isinstance(token, dict) else None
        if not isinstance(id_token_hint, str):
            id_token_hint = None
        code = await create_logout_flow(id_token_hint, settings.app_origin.rstrip("/") + "/")
        logout_path = f"/auth/logout/provider?code={code}"
    await delete_session(session_id)
    response = JSONResponse({"logout_path": logout_path})
    clear_auth_cookies(response)
    return _no_store(response)  # type: ignore[return-value]


@router.get("/logout/provider")
async def logout_provider(code: str) -> RedirectResponse:
    """Completes RP-initiated logout at Keycloak using a one-time server code."""
    if not code or len(code) > 200:
        raise HTTPException(status_code=400, detail="Ungültiger Logout-Code.")
    flow = await consume_logout_flow(code)
    if flow is None:
        return RedirectResponse(settings.app_origin.rstrip("/") + "/", status_code=303)
    logout_endpoint = settings.oidc_logout_url or (
        settings.keycloak_issuer.rstrip("/") + "/protocol/openid-connect/logout"
    )
    query: dict[str, str] = {
        "client_id": settings.keycloak_client_id,
        "post_logout_redirect_uri": settings.app_origin.rstrip("/") + "/",
    }
    id_token_hint = flow.get("id_token_hint")
    if isinstance(id_token_hint, str):
        query["id_token_hint"] = id_token_hint
    return RedirectResponse(f"{logout_endpoint}?{urlencode(query)}", status_code=303)
