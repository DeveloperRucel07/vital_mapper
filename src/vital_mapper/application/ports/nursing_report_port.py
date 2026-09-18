from abc import ABC, abstractmethod
from datetime import datetime

from vital_mapper.domain.value_objects import ClinicalExtraction


class NursingReportPort(ABC):
    """Port fuer die serverseitige Uebergabe freigegebener Pflegeberichte (F-20)."""

    @abstractmethod
    async def submit_nursing_report(
        self,
        patient_ref: str,
        report_text: str,
        extraction: ClinicalExtraction,
        recorded_at: datetime,
        access_token: str,
    ) -> dict[str, object]: ...
