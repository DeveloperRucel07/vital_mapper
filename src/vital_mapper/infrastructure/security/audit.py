from __future__ import annotations

import structlog

logger = structlog.get_logger("audit")


async def log_access(user_id: str, patient_ref: str, action: str) -> None:
    """Schreibt strukturiertes Audit-Log. In Produktion zusaetzlich in eine
    manipulationssichere Senke spiegeln (NF-06), z. B. Append-only-Tabelle
    oder SIEM-Anbindung - das ist im MVP noch nicht umgesetzt (siehe
    Definition of Done, Abschnitt Sicherheit)."""
    logger.info("patient_data_access", user_id=user_id, patient_ref=patient_ref, action=action)
