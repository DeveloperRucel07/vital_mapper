from __future__ import annotations

from abc import ABC, abstractmethod


class PatientAccessPort(ABC):
    """Prüft Zugriff im externen Pflege-Monitoring (F-30/F-31)."""

    @abstractmethod
    async def assert_access(self, patient_ref: str, access_token: str) -> None: ...
