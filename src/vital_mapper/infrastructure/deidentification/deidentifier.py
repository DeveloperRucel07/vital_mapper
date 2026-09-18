from __future__ import annotations

import re

from vital_mapper.application.ports.deidentification_port import DeidentificationPort

DATE_PATTERN = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b")


class StubDeidentifier(DeidentificationPort):
    async def deidentify(self, text: str) -> str:
        return DATE_PATTERN.sub("[DATUM]", text)
