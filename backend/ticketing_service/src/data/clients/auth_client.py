"""
HTTP client for Auth Service.
All cross-service user lookups go through here.
"""

import asyncio
import logging
from typing import Optional

import httpx
from pydantic import BaseModel

from src.config.settings import get_settings
from src.core.exceptions.base import (
    AuthServiceUnavailableError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)


class UserDTO(BaseModel):
    """Minimal user payload returned by Auth Service /api/v1/auth/users/{uuid}"""
    id: str                              # UUID string — matches auth.users.id
    email: str
    role: str                            # "user" | "support_agent" | "team_lead" | "admin"
    is_active: bool = True
    is_verified: bool = False
    customer_tier_id: Optional[int] = None   # from auth.users.customer_tierid


class AuthServiceClient:
    """Thin async wrapper around Auth Service REST API."""

    def __init__(self) -> None:
        self._base_url = get_settings().auth_service_url.rstrip("/")
        self._timeout = httpx.Timeout(5.0)

    async def get_user(self, user_id: str) -> UserDTO:   # FIX: int → str
        """
        GET {AUTH_SERVICE_URL}/api/v1/auth/users/{user_id}
        user_id is the UUID string from the JWT sub claim.
        """
        # FIX: was f"{base}/users/{id}" — missing /api/v1/auth prefix
        url = f"{self._base_url}/api/v1/auth/users/{user_id}"
        logger.debug("auth_client: fetching user_id=%s url=%s", user_id, url)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
        except httpx.TransportError as exc:
            logger.error(
                "auth_client: transport error fetching user_id=%s: %s", user_id, exc
            )
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

    async def get_users_bulk(self, user_ids: list[str]) -> dict[str, UserDTO]:  # FIX: int → str
        """
        Fetch multiple users in parallel.
        Returns {user_id: UserDTO}. Missing users are logged and skipped.
        """
        results: dict[str, UserDTO] = {}

        async def _fetch(uid: str) -> None:
            try:
                results[uid] = await self.get_user(uid)
            except UserNotFoundError:
                logger.warning("auth_client: user_id=%s not found (bulk fetch)", uid)
            except AuthServiceUnavailableError:
                logger.error("auth_client: service unavailable for user_id=%s", uid)

        await asyncio.gather(*[_fetch(uid) for uid in set(user_ids)])
        return results


auth_client = AuthServiceClient()