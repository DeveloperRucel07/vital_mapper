from __future__ import annotations

from vital_mapper.application.ports.interop_gateway_port import InteropGatewayPort
from vital_mapper.application.ports.patient_access_port import PatientAccessPort
from vital_mapper.domain.exceptions import AccessDeniedError
from vital_mapper.infrastructure.interop.gateway_adapter import InteropGatewayError


class GatewayPatientAccessAdapter(PatientAccessPort):
    """Prueft den Patientenkontext ueber das Pflege-Monitoring (F-30/F-31)."""

    def __init__(self, gateway: InteropGatewayPort) -> None:
        self._gateway = gateway

    async def assert_access(self, patient_ref: str, access_token: str) -> None:
        try:
            await self._gateway.request(
                "/interop/v1/patient/read", {"patientId": patient_ref}, access_token
            )
        except InteropGatewayError as exc:
            raise AccessDeniedError("Kein Zugriff auf den Patientenkontext.") from exc
