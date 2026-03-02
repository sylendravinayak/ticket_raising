"""
FastAPI dependency injection.
JWT is already validated upstream by middleware.
current_user_id + current_user_role are injected via request.state.
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.clients.auth_client import auth_client
from src.core.exceptions.base import InvalidTokenError
from src.data.clients.postgres_client import get_db
from src.core.services.ticket_service import TicketService


# ── DB session ─────────────────────────────────────────────────────────────
DBSession = Annotated[AsyncSession, Depends(get_db)]


# ── Current user context (set by JWT middleware) ────────────────────────────
def get_current_user_id(request: Request) -> str:           # FIX: int → str
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise InvalidTokenError("Missing user context — JWT middleware not applied.")
    return str(user_id)                                     # FIX: str() not int()


def get_current_user_role(request: Request) -> str:
    role = getattr(request.state, "user_role", None)
    if not role:
        raise InvalidTokenError("Missing role context — JWT middleware not applied.")
    return str(role)


CurrentUserID   = Annotated[str, Depends(get_current_user_id)]   # FIX: str
CurrentUserRole = Annotated[str, Depends(get_current_user_role)]


# ── TicketService factory ───────────────────────────────────────────────────
def get_ticket_service(db: DBSession) -> TicketService:
    return TicketService(db=db, auth_client=auth_client)


TicketServiceDep = Annotated[TicketService, Depends(get_ticket_service)]