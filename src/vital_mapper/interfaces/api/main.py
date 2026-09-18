from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from vital_mapper.interfaces.api.deps import dispose_database, init_database
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


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await init_database()
    try:
        yield
    finally:
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
