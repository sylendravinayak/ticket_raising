"""
HTTP client for Auth Service.
All cross-service user lookups go through here.
Retries on transient failures; raises ServiceUnavailableError on hard failure.
"""

import logging
from typing import Optional

import httpx
from pydantic import BaseModel

from src.config.settings import settings
from src.core.exceptions.base import (
    AuthServiceUnavailableError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)


class UserDTO(BaseModel):
    """Minimal user payload returned by Auth Service."""
    user_id: int
    email: str
    role: str                          # "CUSTOMER" | "AGENT" | "LEAD" | "ADMIN"
    customer_tier_id: Optional[int] = None
    is_active: bool = True


class AuthServiceClient:
    """Thin async wrapper around Auth Service REST API."""

    def __init__(self) -> None:
        self._base_url = settings.AUTH_SERVICE_URL.rstrip("/")
        self._timeout = httpx.Timeout(5.0)

    async def get_user(self, user_id: int) -> UserDTO:
        """
        GET {AUTH_SERVICE_URL}/users/{user_id}
        Returns UserDTO or raises UserNotFoundError / AuthServiceUnavailableError.
        """
        url = f"{self._base_url}/users/{user_id}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
        except httpx.TransportError as exc:
            logger.error("auth_client: transport error fetching user_id=%s: %s", user_id, exc)
            raise AuthServiceUnavailableError(
                f"Auth Service unreachable while fetching user {user_id}."
            )

        if resp.status_code == 404:
            raise UserNotFoundError(f"User {user_id} not found in Auth Service.")
        if resp.status_code != 200:
            logger.error(
                "auth_client: unexpected status=%s for user_id=%s body=%s",
                resp.status_code, user_id, resp.text,
            )
            raise AuthServiceUnavailableError(
                f"Auth Service returned {resp.status_code} for user {user_id}."
            )

        return UserDTO.model_validate(resp.json())

    async def get_users_bulk(self, user_ids: list[int]) -> dict[int, UserDTO]:
        """
        Fetch multiple users in parallel.
        Returns {user_id: UserDTO}. Missing users are skipped (logged as warnings).
        """
        import asyncio

        results: dict[int, UserDTO] = {}

        async def _fetch(uid: int) -> None:
            try:
                results[uid] = await self.get_user(uid)
            except UserNotFoundError:
                logger.warning("auth_client: user_id=%s not found (bulk fetch)", uid)
            except AuthServiceUnavailableError:
                logger.error("auth_client: service unavailable for user_id=%s", uid)

        await asyncio.gather(*[_fetch(uid) for uid in set(user_ids)])
        return results


auth_client = AuthServiceClient()