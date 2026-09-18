from __future__ import annotations

from typing import Any, Protocol


class InteropGatewayPort(Protocol):
    async def request(
        self, path: str, payload: dict[str, Any], access_token: str
    ) -> dict[str, Any]: ...
