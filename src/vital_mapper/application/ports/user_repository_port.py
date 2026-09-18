from abc import ABC, abstractmethod

from vital_mapper.domain.entities import User


class UserRepositoryPort(ABC):
    """Persistenz-Port fuer Benutzerkonten (F-30)."""

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def save_user(self, user: User) -> None: ...
