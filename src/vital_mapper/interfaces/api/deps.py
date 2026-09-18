from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from vital_mapper.config import settings
from vital_mapper.infrastructure.persistence.models import Base

_engine = create_async_engine(settings.database_url)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        yield session


async def init_database() -> None:
    async with _engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def dispose_database() -> None:
    await _engine.dispose()
