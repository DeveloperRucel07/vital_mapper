import uuid

import pytest

from vital_mapper.application.use_cases.authenticate_user import AuthenticateUserUseCase
from vital_mapper.application.use_cases.create_user import CreateUserUseCase
from vital_mapper.domain.entities import User, UserRole
from vital_mapper.domain.exceptions import InvalidCredentialsError, PasswordPolicyError
from vital_mapper.infrastructure.security.password import ScryptPasswordHasher


class FakeUserRepository:
    def __init__(self, user: User | None = None) -> None:
        self.user = user
        self.saved: User | None = None

    async def get_by_username(self, username: str) -> User | None:
        if self.user is not None and self.user.username == username:
            return self.user
        return None

    async def save_user(self, user: User) -> None:
        self.saved = user


def test_scrypt_hash_roundtrip_does_not_store_plaintext() -> None:
    hasher = ScryptPasswordHasher()
    plain_text = "synthetic-strong-password"

    encoded_hash = hasher.hash_password(plain_text)

    assert plain_text not in encoded_hash
    assert hasher.verify_password(plain_text, encoded_hash)
    assert not hasher.verify_password("wrong-password", encoded_hash)


async def test_authentication_returns_active_user() -> None:
    hasher = ScryptPasswordHasher()
    user = User(
        id=uuid.uuid4(),
        username="pflegekraft-test",
        password_hash=hasher.hash_password("synthetic-strong-password"),
        role=UserRole.PFLEGEFACHKRAFT,
        active=True,
    )
    use_case = AuthenticateUserUseCase(FakeUserRepository(user), hasher)  # type: ignore[arg-type]

    authenticated = await use_case.execute(user.username, "synthetic-strong-password")

    assert authenticated.id == user.id
    assert authenticated.role == UserRole.PFLEGEFACHKRAFT


@pytest.mark.parametrize(
    "username,password", [("unknown", "wrong-password"), ("pflegekraft-test", "wrong-password")]
)
async def test_authentication_hides_invalid_credentials(username: str, password: str) -> None:
    use_case = AuthenticateUserUseCase(FakeUserRepository(), ScryptPasswordHasher())  # type: ignore[arg-type]

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(username, password)


async def test_create_user_rejects_short_password() -> None:
    repository = FakeUserRepository()
    use_case = CreateUserUseCase(repository, ScryptPasswordHasher())  # type: ignore[arg-type]

    with pytest.raises(PasswordPolicyError):
        await use_case.execute("pflegekraft-test", "short", UserRole.PFLEGEFACHKRAFT)

    assert repository.saved is None
