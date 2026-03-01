"""
Ticket routes — all steps wired up.

POST   /tickets               create ticket
PUT    /tickets/{id}/status   transition status
POST   /tickets/{id}/assign   assign ticket
GET    /tickets/me            customer's own tickets
GET    /tickets/{id}          ticket detail
GET    /tickets/{id}/logs     audit trail
GET    /tickets               all tickets (Lead/Admin only)
"""

from fastapi import APIRouter, Depends, Query, status
from typing import Optional

from src.api.rest.dependencies import (
    CurrentUserID,
    CurrentUserRole,
    TicketServiceDep,
)
from src.constants.enum import (
    Priority,
    Severity,
    TicketStatus,
    UserRole,
)
from src.core.exceptions.base import InsufficientPermissionsError
from src.schemas.common_schema import PaginatedResponse
from src.schemas.ticket_schema import (
    TicketAssignRequest,
    TicketBriefResponse,
    TicketCreateRequest,
    TicketDetailResponse,
    TicketEventResponse,
    TicketListFilters,
    TicketStatusUpdateRequest,
)

router = APIRouter()


# ══════════════════════════════════════════════════════════
# POST /tickets — Create ticket
# ══════════════════════════════════════════════════════════

@router.post(
    "",
    response_model=TicketDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ticket",
)
async def create_ticket(
    payload: TicketCreateRequest,
    svc: TicketServiceDep,
    user_id: CurrentUserID,
):
    ticket = await svc.create_ticket(payload, current_user_id=user_id)
    return TicketDetailResponse.model_validate(ticket)


# ══════════════════════════════════════════════════════════
# PUT /tickets/{id}/status — Transition status
# ══════════════════════════════════════════════════════════

@router.put(
    "/{ticket_id}/status",
    response_model=TicketBriefResponse,
    summary="Transition ticket status",
)
async def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdateRequest,
    svc: TicketServiceDep,
    user_id: CurrentUserID,
):
    ticket = await svc.transition_status(ticket_id, payload, current_user_id=user_id)
    return TicketBriefResponse.model_validate(ticket)


# ══════════════════════════════════════════════════════════
# POST /tickets/{id}/assign — Assign ticket
# ══════════════════════════════════════════════════════════

@router.post(
    "/{ticket_id}/assign",
    response_model=TicketBriefResponse,
    summary="Assign ticket to an agent",
)
async def assign_ticket(
    ticket_id: int,
    payload: TicketAssignRequest,
    svc: TicketServiceDep,
    user_id: CurrentUserID,
    user_role: CurrentUserRole,
):
    ticket = await svc.assign_ticket(
        ticket_id, payload,
        current_user_id=user_id,
        current_user_role=user_role,
    )
    return TicketBriefResponse.model_validate(ticket)


# ══════════════════════════════════════════════════════════
# GET /tickets/me — Customer's own tickets
# ══════════════════════════════════════════════════════════

@router.get(
    "/me",
    response_model=PaginatedResponse[TicketBriefResponse],
    summary="Get my tickets (customer)",
)
async def get_my_tickets(
    svc: TicketServiceDep,
    user_id: CurrentUserID,
    status_filter: Optional[TicketStatus] = Query(default=None, alias="status"),
    priority: Optional[Priority] = Query(default=None),
    severity: Optional[Severity] = Query(default=None),
    is_breached: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    filters = TicketListFilters(
        status=status_filter,
        priority=priority,
        severity=severity,
        is_breached=is_breached,
        page=page,
        page_size=page_size,
    )
    total, tickets = await svc.get_my_tickets(user_id, filters)
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[TicketBriefResponse.model_validate(t) for t in tickets],
    )


# ══════════════════════════════════════════════════════════
# GET /tickets/{id} — Ticket detail
# ══════════════════════════════════════════════════════════

@router.get(
    "/{ticket_id}",
    response_model=TicketDetailResponse,
    summary="Get ticket details",
)
async def get_ticket(
    ticket_id: int,
    svc: TicketServiceDep,
    user_id: CurrentUserID,
    user_role: CurrentUserRole,
):
    ticket = await svc.get_ticket_detail(ticket_id, user_id, user_role)
    return TicketDetailResponse.model_validate(ticket)


# ══════════════════════════════════════════════════════════
# GET /tickets/{id}/logs — Audit trail
# ══════════════════════════════════════════════════════════

@router.get(
    "/{ticket_id}/logs",
    response_model=list[TicketEventResponse],
    summary="Get ticket audit trail",
)
async def get_ticket_logs(
    ticket_id: int,
    svc: TicketServiceDep,
    user_id: CurrentUserID,
    user_role: CurrentUserRole,
):
    # Non-customers can always view; customers only their own (detail check covers it)
    role = UserRole(user_role)
    if role == UserRole.CUSTOMER:
        await svc.get_ticket_detail(ticket_id, user_id, user_role)  # triggers ownership check

    events = await svc.get_ticket_logs(ticket_id)
    return [TicketEventResponse.model_validate(e) for e in events]


# ══════════════════════════════════════════════════════════
# GET /tickets — All tickets (Lead / Admin only)
# ════════════════���═════════════════════════════════════════

@router.get(
    "",
    response_model=PaginatedResponse[TicketBriefResponse],
    summary="List all tickets (Lead/Admin only)",
)
async def list_all_tickets(
    svc: TicketServiceDep,
    user_id: CurrentUserID,
    user_role: CurrentUserRole,
    status_filter: Optional[TicketStatus] = Query(default=None, alias="status"),
    priority: Optional[Priority] = Query(default=None),
    severity: Optional[Severity] = Query(default=None),
    assignee_id: Optional[int] = Query(default=None),
    is_breached: Optional[bool] = Query(default=None),
    is_escalated: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    role = UserRole(user_role)
    if role not in (UserRole.LEAD, UserRole.ADMIN):
        raise InsufficientPermissionsError("Only Lead or Admin can list all tickets.")

    filters = TicketListFilters(
        status=status_filter,
        priority=priority,
        severity=severity,
        assignee_id=assignee_id,
        is_breached=is_breached,
        is_escalated=is_escalated,
        page=page,
        page_size=page_size,
    )
    total, tickets = await svc.get_all_tickets(filters)
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[TicketBriefResponse.model_validate(t) for t in tickets],
    )