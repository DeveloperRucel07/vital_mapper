from abc import ABC, abstractmethod

from vital_mapper.domain.value_objects import ClinicalExtraction


class ExtractionPort(ABC):
    @abstractmethod
    async def extract(self, transcript_text: str) -> tuple[ClinicalExtraction, str]:
        """Gibt (strukturierte Extraktion, Modellversion) zurueck."""
