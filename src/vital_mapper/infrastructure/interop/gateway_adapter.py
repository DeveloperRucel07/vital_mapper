from __future__ import annotations

from typing import Any

import httpx

from vital_mapper.config import settings


class InteropGatewayError(RuntimeError):
    """Raised when the gateway cannot provide a safe upstream response (NF-30)."""


class HttpInteropGatewayAdapter:
    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or settings.interop_gateway_url).rstrip("/")

    async def request(
        self, path: str, payload: dict[str, Any], access_token: str
    ) -> dict[str, Any]:
        if not path.startswith("/interop/v1/"):
            raise ValueError("Gateway path is outside the versioned interoperability contract.")
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=settings.interop_timeout_seconds
            ) as client:
                response = await client.post(
                    path,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/fhir+json, application/json",
                    },
                )
        except httpx.HTTPError as exc:
            raise InteropGatewayError("Interoperabilitäts-Gateway ist nicht erreichbar.") from exc
        if response.status_code in {401, 403}:
            raise InteropGatewayError("Zugriff auf den Patientenkontext wurde verweigert.")
        if response.status_code >= 400:
            raise InteropGatewayError("Das Monitoring konnte die Anfrage nicht verarbeiten.")
        try:
            result = response.json()
        except ValueError as exc:
            raise InteropGatewayError("Das Monitoring lieferte eine ungültige Antwort.") from exc
        if not isinstance(result, dict):
            raise InteropGatewayError("Das Monitoring lieferte ein ungültiges Antwortformat.")
        return result
