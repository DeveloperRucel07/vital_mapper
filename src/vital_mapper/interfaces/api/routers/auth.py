"""Username-/Passwort-Authentifizierung und Benutzerverwaltung (F-30)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from vital_mapper.application.use_cases.authenticate_user import AuthenticateUserUseCase
from vital_mapper.application.use_cases.create_user import CreateUserUseCase
from vital_mapper.domain.entities import UserRole
from vital_mapper.domain.exceptions import (
    InvalidCredentialsError,
    PasswordPolicyError,
    UserAlreadyExistsError,
    UsernamePolicyError,
)
from vital_mapper.infrastructure.persistence.user_repository import PostgresUserRepository
from vital_mapper.infrastructure.security.auth import CurrentUser, create_access_token
from vital_mapper.infrastructure.security.password import ScryptPasswordHasher
from vital_mapper.infrastructure.security.rbac import require_role
from vital_mapper.interfaces.api.deps import get_session
from vital_mapper.interfaces.api.schemas import (
    CreateUserRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    """Authentifiziert einen Benutzer und gibt ein kurzlebiges JWT aus (F-30)."""
    use_case = AuthenticateUserUseCase(PostgresUserRepository(session), ScryptPasswordHasher())
    try:
        user = await use_case.execute(body.username, body.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungueltige Zugangsdaten.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return TokenResponse(access_token=create_access_token(user))


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    session: AsyncSession = Depends(get_session),
    _admin: CurrentUser = Depends(require_role(UserRole.ADMINISTRATOR)),
) -> UserResponse:
    """Legt ein Konto nur durch einen Administrator an (F-30)."""
    use_case = CreateUserUseCase(PostgresUserRepository(session), ScryptPasswordHasher())
    try:
        user = await use_case.execute(body.username, body.password, body.role)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (PasswordPolicyError, UsernamePolicyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        active=user.active,
    )
