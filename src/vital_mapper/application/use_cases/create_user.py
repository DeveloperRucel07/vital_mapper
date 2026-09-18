import uuid

from vital_mapper.application.ports.password_hasher_port import PasswordHasherPort
from vital_mapper.application.ports.user_repository_port import UserRepositoryPort
from vital_mapper.domain.entities import User, UserRole
from vital_mapper.domain.exceptions import (
    PasswordPolicyError,
    UserAlreadyExistsError,
    UsernamePolicyError,
)

MIN_PASSWORD_LENGTH = 12
MIN_USERNAME_LENGTH = 3


class CreateUserUseCase:
    """Legt ein Benutzerkonto mit gehashtem Passwort an (F-30)."""

    def __init__(self, users: UserRepositoryPort, hasher: PasswordHasherPort) -> None:
        self._users = users
        self._hasher = hasher

    async def execute(self, username: str, password: str, role: UserRole) -> User:
        normalized_username = username.strip()
        if len(normalized_username) < MIN_USERNAME_LENGTH:
            raise UsernamePolicyError(
                f"Der Benutzername muss mindestens {MIN_USERNAME_LENGTH} Zeichen enthalten."
            )
        if len(password) < MIN_PASSWORD_LENGTH:
            raise PasswordPolicyError(
                f"Das Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen enthalten."
            )
        if await self._users.get_by_username(normalized_username) is not None:
            raise UserAlreadyExistsError("Der Benutzername ist bereits vergeben.")
        user = User(
            id=uuid.uuid4(),
            username=normalized_username,
            password_hash=self._hasher.hash_password(password),
            role=role,
            active=True,
        )
        await self._users.save_user(user)
        return user
