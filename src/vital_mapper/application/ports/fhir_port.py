from abc import ABC, abstractmethod
from typing import Any

from vital_mapper.domain.value_objects import ClinicalExtraction


class FhirPort(ABC):
    @abstractmethod
    async def submit_observation_bundle(
        self, patient_ref: str, data: ClinicalExtraction
    ) -> list[str]:
        """Erzeugt und uebermittelt FHIR-Ressourcen, gibt Resource-IDs zurueck."""

    @abstractmethod
    async def submit_provenance(
        self, target_resource_ids: list[str], agent_id: str, meta: dict[str, Any]
    ) -> str:
        """Erzeugt eine Provenance-Ressource fuer den Audit-Trail (F-21/F-22/F-33)."""
