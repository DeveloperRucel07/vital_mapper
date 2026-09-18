from abc import ABC, abstractmethod


class DeidentificationPort(ABC):
    @abstractmethod
    async def deidentify(self, text: str) -> str:
        """Maskiert Namen, Orte, Datums-/Zeitangaben und sonstige
        Quasi-Identifikatoren."""
