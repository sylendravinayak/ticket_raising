
import uuid
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.security import decode_token
from src.data.clients.postgres_client import get_db
from src.core.exceptions.auth import (
    AuthenticationException,
    AuthorizationException,
    InvalidTokenTypeException,
    TokenExpiredException,
)
from src.data.models.postgres.user import User
from src.data.repositories.user_repository import UserRepository


bearer_scheme = HTTPBearer(auto_error=True)


async def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> dict[str, Any]:
    """
    Extract and cryptographically verify the JWT from the Authorization header.
    """
    try:
        return decode_token(credentials.credentials)
    except ExpiredSignatureError:
        raise TokenExpiredException()
    except JWTError:
        raise AuthenticationException()


async def get_current_user(
    payload: Annotated[dict[str, Any], Depends(get_token_payload)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Resolve the authenticated user from a valid access token.
    """
    if payload.get("token_type") != "access":
        raise InvalidTokenTypeException()

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise AuthenticationException()

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationException()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if not user or not user.is_active:
        raise AuthenticationException()

    return user


async def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Ensures the user account is active.
    """
    if not user.is_active:
        raise AuthorizationException("Account is disabled")
    return user


def role_required(required_role: str) -> Callable[..., Any]:
    """
    Dependency factory for role-based access control.
        Usage: Depends(role_required("admin")) to restrict access to admins only.
        Checks the "role" claim in the JWT against the required role.
    """

    async def _check(
        user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if user.role != required_role:
            raise AuthorizationException(
                f"Role '{required_role}' required"
            )
        return user

    return _check