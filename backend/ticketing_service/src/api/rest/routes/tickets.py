"""
Ticket routes.

POST   /tickets               create ticket
PUT    /tickets/{id}/status   transition status
POST   /tickets/{id}/assign   assign ticket
GET    /tickets/me            caller's own tickets (role-aware)
GET    /tickets/{id}          ticket detail
GET    /tickets               all tickets (team_lead / admin only)
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api.rest.dependencies import (
    CurrentUserID,
    CurrentUserRole,
    TicketServiceDep,
)
from src.constants.enum import Priority, Severity, TicketStatus, UserRole
from src.control.assignment_agent.workflow import run_auto_assign
from src.control.assignment_agent.workflow import run_auto_assign
from src.schemas.common_schema import PaginatedResponse
from src.schemas.ticket_schema import (
    TicketAssignRequest,
    TicketBriefResponse,
    TicketCreateRequest,
    TicketDetailResponse,
    TicketListFilters,
    TicketStatusUpdateRequest,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


# ── CREATE ────────────────────────────────────────────────────────────────────
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


# ── MY TICKETS (role-aware) ───────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=PaginatedResponse[TicketBriefResponse],
    summary="Get my tickets — role-aware",
    description=(
        "**user** → tickets they raised  \n"
        "**support_agent** → tickets assigned to them  \n"
        "**team_lead / admin** → all tickets"
    ),
)
async def get_my_tickets(
    svc: TicketServiceDep,
    user_id: CurrentUserID,
    user_role: CurrentUserRole,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[TicketStatus] = Query(default=None, alias="status"),
    severity: Optional[Severity] = Query(default=None),
    priority: Optional[Priority] = Query(default=None),
    is_breached: Optional[bool] = Query(default=None),
):
    filters = TicketListFilters(
        page=page,
        page_size=page_size,
        status=status_filter,
        severity=severity,
        priority=priority,
        is_breached=is_breached,
    )
    total, tickets = await svc.get_my_tickets(
        current_user_id=user_id,
        current_user_role=user_role,  
        filters=filters,
    )
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[TicketBriefResponse.model_validate(t) for t in tickets],
    )


# ── ALL TICKETS (lead / admin only) ───────────────────────────────────────────
@router.get(
    "",
    response_model=PaginatedResponse[TicketBriefResponse],
    summary="List all tickets — team_lead / admin only",
)
async def list_all_tickets(
    svc: TicketServiceDep,
    user_id: CurrentUserID,
    user_role: CurrentUserRole,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[TicketStatus] = Query(default=None, alias="status"),
    severity: Optional[Severity] = Query(default=None),
    priority: Optional[Priority] = Query(default=None),
    is_breached: Optional[bool] = Query(default=None),
    is_escalated: Optional[bool] = Query(default=None),
    customer_id: Optional[str] = Query(default=None),
    assignee_id: Optional[str] = Query(default=None),
):
    filters = TicketListFilters(
        page=page,
        page_size=page_size,
        status=status_filter,
        severity=severity,
        priority=priority,
        is_breached=is_breached,
        is_escalated=is_escalated,
        customer_id=customer_id,
        assignee_id=assignee_id,
    )
    total, tickets = await svc.get_all_tickets(
        filters=filters,
        current_user_role=user_role,
    )
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[TicketBriefResponse.model_validate(t) for t in tickets],
    )


# ── TICKET DETAIL ─────────────────────────────────────────────────────────────
@router.get(
    "/{ticket_id}",
    response_model=TicketDetailResponse,
    summary="Get ticket detail",
)
async def get_ticket(
    ticket_id: int,
    svc: TicketServiceDep,
    user_id: CurrentUserID,
    user_role: CurrentUserRole,
):
    ticket = await svc.get_ticket_detail(
        ticket_id=ticket_id,
        current_user_id=user_id,
        current_user_role=user_role,
    )
    return TicketDetailResponse.model_validate(ticket)


# ── STATUS TRANSITION ─────────────────────────────────────────────────────────
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
    user_role: CurrentUserRole,
):
    ticket = await svc.transition_status(
        ticket_id, payload,
        current_user_id=user_id,
        current_user_role=user_role,
    )
    return TicketBriefResponse.model_validate(ticket)


# ── ASSIGN ────────────────────────────────────────────────────────────────────
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



@router.post(
    "/{ticket_id}/auto-assign",
    summary="AI-powered automatic ticket assignment",
    status_code=status.HTTP_200_OK,
)
async def auto_assign_ticket(
    ticket_id: int,
    ticket_title: str,          # pass via query param or extend with a request body
    ticket_priority: str,
    user_id: CurrentUserID,
    user_role: CurrentUserRole,
):
    role = UserRole(user_role)
    if role not in (UserRole.LEAD, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team_lead or admin can trigger auto-assignment.",
        )

    result = await run_auto_assign(
        ticket_id=ticket_id,
        ticket_title=ticket_title,
        ticket_priority=ticket_priority,
        assigner_id=user_id,
        assigner_role=user_role,
    )
    return result