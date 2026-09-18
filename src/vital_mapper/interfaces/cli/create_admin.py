"""Kontrollierte Erstprovisionierung eines Administratorkontos (F-30)."""

from __future__ import annotations

import asyncio

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from vital_mapper.application.use_cases.create_user import CreateUserUseCase
from vital_mapper.config import settings
from vital_mapper.domain.entities import UserRole
from vital_mapper.infrastructure.persistence.models import Base
from vital_mapper.infrastructure.persistence.user_repository import PostgresUserRepository
from vital_mapper.infrastructure.security.password import ScryptPasswordHasher

logger = structlog.get_logger("bootstrap")


async def create_initial_admin() -> None:
    """Erstellt Tabellen und den ersten Administrator aus Deployment-Secrets (F-30)."""
    username = settings.bootstrap_admin_username
    password = settings.bootstrap_admin_password
    if not username or not password:
        raise RuntimeError(
            "BOOTSTRAP_ADMIN_USERNAME und BOOTSTRAP_ADMIN_PASSWORD muessen gesetzt sein."
        )

    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            user = await CreateUserUseCase(
                PostgresUserRepository(session), ScryptPasswordHasher()
            ).execute(
                username,
                password,
                UserRole.ADMINISTRATOR,
            )
            logger.info("initial_admin_created", user_id=str(user.id))
    finally:
        await engine.dispose()


def main() -> None:
    """CLI-Einstiegspunkt fuer die kontrollierte Erstinitialisierung (F-30)."""
    asyncio.run(create_initial_admin())


if __name__ == "__main__":
    main()
