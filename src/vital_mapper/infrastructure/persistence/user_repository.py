from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from vital_mapper.application.ports.user_repository_port import UserRepositoryPort
from vital_mapper.domain.entities import User, UserRole
from vital_mapper.domain.exceptions import UserAlreadyExistsError
from vital_mapper.infrastructure.persistence.models import UserModel


class PostgresUserRepository(UserRepositoryPort):
    """PostgreSQL-Adapter fuer Benutzerkonten (F-30)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_username(self, username: str) -> User | None:
        model = await self._session.scalar(select(UserModel).where(UserModel.username == username))
        if model is None:
            return None
        return User(
            id=model.id,
            username=model.username,
            password_hash=model.password_hash,
            role=UserRole(model.role),
            active=model.active,
        )

    async def save_user(self, user: User) -> None:
        self._session.add(
            UserModel(
                id=user.id,
                username=user.username,
                password_hash=user.password_hash,
                role=user.role.value,
                active=user.active,
            )
        )
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise UserAlreadyExistsError("Der Benutzername ist bereits vergeben.") from exc
