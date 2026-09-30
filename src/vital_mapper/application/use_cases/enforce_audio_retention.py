from __future__ import annotations

from datetime import UTC, datetime, timedelta

from vital_mapper.application.ports.audio_storage_port import AudioStoragePort
from vital_mapper.application.ports.repository_port import RepositoryPort
from vital_mapper.domain.entities import Recording


class EnforceAudioRetentionUseCase:
    """Loescht Rohaudio nach der konfigurierten Aufbewahrungsdauer (F-27)."""

    def __init__(
        self,
        repository: RepositoryPort,
        audio_storage: AudioStoragePort,
        retention_days: int,
    ) -> None:
        if retention_days < 1:
            raise ValueError("Die Audio-Aufbewahrungsdauer muss mindestens einen Tag betragen.")
        self._repository = repository
        self._audio_storage = audio_storage
        self._retention_days = retention_days

    async def execute(
        self,
        *,
        now: datetime | None = None,
        batch_size: int = 100,
    ) -> list[Recording]:
        """Loescht alle faelligen Audiodateien in begrenzten Batches.

        Die Datei wird vor dem Leeren der Datenbankreferenz geloescht. Schlaegt
        die Datenbankaktualisierung fehl, ist ein erneuter Lauf dadurch sicher:
        das Dateiloeschen ist idempotent und wird wiederholt.
        """

        if batch_size < 1:
            raise ValueError("Die Batch-Groesse muss positiv sein.")
        reference_time = now or datetime.now(UTC)
        if reference_time.tzinfo is None:
            raise ValueError("Der Referenzzeitpunkt muss eine Zeitzone enthalten.")
        cutoff = reference_time - timedelta(days=self._retention_days)
        deleted: list[Recording] = []

        while True:
            expired = await self._repository.list_recordings_with_expired_audio(cutoff, batch_size)
            if not expired:
                break
            for recording in expired:
                await self._audio_storage.delete(recording.audio_ref)
                await self._repository.mark_audio_deleted(recording.id)
                deleted.append(recording)
            if len(expired) < batch_size:
                break

        return deleted
