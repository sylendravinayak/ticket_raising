

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.clients.postgres_client import get_db
from src.api.rest.dependencies.auth import get_current_active_user, get_token_payload
from src.data.models.postgres.user import User
from src.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
    UserResponse,
)
from src.core.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)


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




@router.post(
    "/login",
    response_model=TokenResponse
)
@limiter.limit("5/minute")
async def login(
    request: Request,  
    data: LoginRequest,
    service: Annotated[AuthService, Depends(_get_service)],
) -> TokenResponse:
    return await service.login(data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token",
    description=(
        "Exchange a valid refresh token for a new token pair. "
    ),
)
async def refresh(
    data: RefreshRequest,
    service: Annotated[AuthService, Depends(_get_service)],
) -> TokenResponse:
    return await service.refresh(data.refresh_token, data.device_id)


@router.post(
    "/logout",
    summary="Logout and revoke refresh token",
    description=(
        "Revokes the provided refresh token. "
        
    ),
)
async def logout(
    data: LogoutRequest,
    service: Annotated[AuthService, Depends(_get_service)],
    
    _current_user: Annotated[User, Depends(get_current_active_user)],
) -> str:
    await service.logout(data.refresh_token)
    return "logout successful"

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description=(
        "Returns the profile of the currently authenticated user. "
        "Requires a valid Bearer access token."
    ),
)
async def me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    return UserResponse.model_validate(current_user)