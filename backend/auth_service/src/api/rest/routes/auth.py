

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Request, Response
from src.utils.security import set_auth_cookies, clear_auth_cookies
from src.schemas.auth import AccessTokenResponse
from src.api.rest.dependencies.auth import get_current_active_user
from src.core.services.auth_service import AuthService
from src.data.clients.postgres_client import get_db
from src.data.models.postgres.user import User
from src.observability.logging.logger import get_logger
from fastapi import HTTPException
from src.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
    UserResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

def _get_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    return AuthService(session=session)




@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=201,
    summary="Register a new user",
    description=(
        "Create a new user account. "

    ),
)
async def signup(
    data: SignupRequest,
    service: Annotated[AuthService, Depends(_get_service)],
) -> SignupResponse:
    user = await service.signup(data)

    return SignupResponse(user=user)

@router.post("/login", response_model=AccessTokenResponse)
async def login(
    data: LoginRequest,
    response: Response,
    service: Annotated[AuthService, Depends(_get_service)],
) -> AccessTokenResponse:
    tokens = await service.login(data)
    set_auth_cookies(response, tokens.refresh_token)
    return AccessTokenResponse(access_token=tokens.access_token, expires_in=tokens.expires_in)

@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(_get_service)],
) -> AccessTokenResponse:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")
    tokens = await service.refresh(refresh_token)
    set_auth_cookies(response, tokens.refresh_token)
    return AccessTokenResponse(access_token=tokens.access_token, expires_in=tokens.expires_in)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(_get_service)],
    _current_user: Annotated[User, Depends(get_current_active_user)],
) -> str:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")
    await service.logout(refresh_token)
    clear_auth_cookies(response)
    return "logout successful"

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description=(
        "Returns the profile of the currently authenticated user. "
    ),
)
async def me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    return UserResponse.model_validate(current_user)
