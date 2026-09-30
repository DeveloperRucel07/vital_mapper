import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from vital_mapper.application.use_cases.enforce_audio_retention import (
    EnforceAudioRetentionUseCase,
)
from vital_mapper.config import settings
from vital_mapper.infrastructure.persistence.repository import PostgresRepository
from vital_mapper.infrastructure.security.audio_storage import EncryptedAudioStorage
from vital_mapper.infrastructure.security.audit import log_access
from vital_mapper.interfaces.api.deps import dispose_database, init_database, session_scope
from vital_mapper.interfaces.api.routers import (
    auth,
    drafts,
    extractions,
    health,
    interop,
    oidc_auth,
    recordings,
    transcripts,
)

logger = structlog.get_logger("application")


async def _encrypt_legacy_transcripts() -> int:
    async with session_scope() as session:
        return await PostgresRepository(session).encrypt_legacy_transcripts()


async def _enforce_audio_retention_once() -> int:
    async with session_scope() as session:
        recordings = await EnforceAudioRetentionUseCase(
            PostgresRepository(session),
            EncryptedAudioStorage(settings.audio_storage_path),
            settings.audio_retention_days,
        ).execute()
    for recording in recordings:
        await log_access("system:audio-retention", recording.patient_ref, "delete_expired_audio")
    return len(recordings)


async def _audio_retention_worker() -> None:
    """Setzt die maximale Audioaufbewahrung fortlaufend durch (F-27)."""

    while True:
        try:
            deleted_count = await _enforce_audio_retention_once()
            logger.info("audio_retention_completed", deleted_count=deleted_count)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("audio_retention_failed")
        await asyncio.sleep(settings.audio_retention_check_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await init_database()
    migrated_transcripts = await _encrypt_legacy_transcripts()
    logger.info("transcript_encryption_migration_completed", migrated_count=migrated_transcripts)
    retention_task = asyncio.create_task(
        _audio_retention_worker(), name="vital-mapper-audio-retention"
    )
    try:
        yield
    finally:
        retention_task.cancel()
        try:
            await retention_task
        except asyncio.CancelledError:
            pass
        await dispose_database()


app = FastAPI(title="Vital Mapper Backend", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(oidc_auth.router)
app.include_router(interop.router)
app.include_router(drafts.router)
app.include_router(recordings.router)
app.include_router(extractions.router)
app.include_router(transcripts.router)
