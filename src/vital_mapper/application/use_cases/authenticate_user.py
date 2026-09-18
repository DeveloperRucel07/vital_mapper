from vital_mapper.application.ports.password_hasher_port import PasswordHasherPort
from vital_mapper.application.ports.user_repository_port import UserRepositoryPort
from vital_mapper.domain.entities import User
from vital_mapper.domain.exceptions import InvalidCredentialsError


class AuthenticateUserUseCase:
    """Prueft Username/Passwort ohne Benutzerexistenz zu verraten (F-30)."""

    def __init__(self, users: UserRepositoryPort, hasher: PasswordHasherPort) -> None:
        self._users = users
        self._hasher = hasher

    async def execute(self, username: str, password: str) -> User:
        normalized_username = username.strip()
        user = await self._users.get_by_username(normalized_username)
        if (
            user is None
            or not user.active
            or not self._hasher.verify_password(password, user.password_hash)
        ):
            raise InvalidCredentialsError("Ungueltige Zugangsdaten.")
        return user
