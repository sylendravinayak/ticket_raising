"""
Ticket repository — manages the ``tickets`` table ONLY.

This repository must NOT query or mutate any other table.
Cross-table orchestration belongs in the service layer.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.constants.enum import QueueType, RoutingStatus, TicketStatus
from src.data.models.postgres.ticket import Ticket
from src.schemas.ticket_schema import TicketListFilters


_EAGER = [
    selectinload(Ticket.attachments),
    selectinload(Ticket.comments),
    selectinload(Ticket.events),
]


class TicketRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── READ ─────────────────────────────────────────────────────────────────

    async def get_by_id(self, ticket_id: int, eager: bool = True) -> Optional[Ticket]:
        stmt = select(Ticket).where(Ticket.ticket_id == ticket_id)
        if eager:
            stmt = stmt.options(*_EAGER)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_number(self, ticket_number: str) -> Optional[Ticket]:
        result = await self.db.execute(
            select(Ticket)
            .where(Ticket.ticket_number == ticket_number)
            .options(*_EAGER)
        )
        return result.scalar_one_or_none()

    async def next_ticket_number(self) -> str:
        """
        Generates TKT-XXXX.
        Uses COUNT + 1; safe under the DB-level unique constraint on ticket_number.
        """
        result = await self.db.execute(select(func.count(Ticket.ticket_id)))
        count = result.scalar_one()
        return f"TKT-{count + 1:04d}"

    async def list_for_customer(
        self, customer_id: str, filters: TicketListFilters
    ) -> tuple[int, list[Ticket]]:
        stmt = select(Ticket).where(Ticket.customer_id == customer_id)
        stmt = self._apply_filters(stmt, filters)
        return await self._paginate(stmt, filters)

    async def list_all(
        self, filters: TicketListFilters
    ) -> tuple[int, list[Ticket]]:
        stmt = select(Ticket).options(*_EAGER)
        stmt = self._apply_filters(stmt, filters)
        return await self._paginate(stmt, filters)

    async def get_breachable(self, now: datetime) -> list[Ticket]:
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.resolution_due_at < now,
                Ticket.status.not_in([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
                Ticket.is_breached == False,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def get_escalatable(self, now: datetime) -> list[Ticket]:
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.is_breached == True,   # noqa: E712
                Ticket.is_escalated == False, # noqa: E712
                Ticket.status.not_in([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            )
        )
        return list(result.scalars().all())

    async def get_resolved_by_assignees(
        self, assignee_ids: list[str],
    ) -> list[Ticket]:
        """
        Return tickets in RESOLVED or CLOSED status for the given assignee IDs.
        Used by the assignment agent to understand each agent's historical expertise.
        """
        if not assignee_ids:
            return []
        result = await self.db.execute(
            select(Ticket)
            .where(
                Ticket.assignee_id.in_(assignee_ids),
                Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            )
            .order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_lead_timed_out_tickets(self, cutoff: datetime) -> list[Ticket]:
        """
        Tickets that were assigned to a lead after AI failure but the lead
        hasn't re-assigned within the timeout window.  Condition:
          - routing_status = AI_FAILED
          - queue_type = DIRECT  (still assigned, not yet open)
          - lead_assigned_at < cutoff
          - assignee_id IS NOT NULL (still assigned to lead)
        """
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.routing_status == RoutingStatus.AI_FAILED.value,
                Ticket.queue_type == QueueType.DIRECT.value,
                Ticket.lead_assigned_at.isnot(None),
                Ticket.lead_assigned_at < cutoff,
                Ticket.assignee_id.isnot(None),
                Ticket.status.in_([
                    TicketStatus.ACKNOWLEDGED,
                    TicketStatus.OPEN,
                    TicketStatus.NEW,
                ]),
            )
        )
        return list(result.scalars().all())

    async def get_response_sla_candidates(self, now: datetime) -> list[Ticket]:
        """
        Tickets whose response SLA *may* be breached right now.
        The actual breach check is done by SLAService.check_response_breach().
        """
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.response_sla_started_at.isnot(None),
                Ticket.response_sla_deadline_minutes.isnot(None),
                Ticket.response_sla_completed_at.is_(None),
                Ticket.response_sla_breached_at.is_(None),
                Ticket.status.in_([
                    TicketStatus.NEW,
                    TicketStatus.ACKNOWLEDGED,
                    TicketStatus.OPEN,
                ]),
            )
        )
        return list(result.scalars().all())

    async def get_resolution_sla_candidates(self, now: datetime) -> list[Ticket]:
        """
        Tickets whose resolution SLA *may* be breached right now.
        The actual breach check is done by SLAService.check_resolution_breach().
        """
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.resolution_sla_started_at.isnot(None),
                Ticket.resolution_sla_deadline_minutes.isnot(None),
                Ticket.resolution_sla_completed_at.is_(None),
                Ticket.resolution_sla_breached_at.is_(None),
                Ticket.resolution_sla_paused_at.is_(None),
                Ticket.status == TicketStatus.IN_PROGRESS,
            )
        )
        return list(result.scalars().all())

    async def get_auto_closeable(self, cutoff: datetime) -> list[Ticket]:
        """
        Tickets in RESOLVED status whose resolution was completed before *cutoff*
        and have not yet been auto-closed.
        """
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.status == TicketStatus.RESOLVED,
                Ticket.auto_closed == False,  # noqa: E712
                Ticket.resolution_sla_completed_at.isnot(None),
                Ticket.resolution_sla_completed_at <= cutoff,
            )
        )
        return list(result.scalars().all())

    # ── WRITE ────────────────────────────────────────────────────────────────

    async def create(self, ticket: Ticket) -> Ticket:
        """Persist a new ticket and return it with all relations loaded."""
        self.db.add(ticket)
        await self.db.flush()
        # Re-fetch with eager relations so Pydantic can serialise immediately
        return await self.get_by_id(ticket.ticket_id, eager=True)

    async def save(self, ticket: Ticket) -> Ticket:
        """Update an existing ticket and return it with relations loaded."""
        self.db.add(ticket)
        await self.db.flush()
        return await self.get_by_id(ticket.ticket_id, eager=True)

    # ── INTERNAL ─────────────────────────────────────────────────────────────

    def _apply_filters(self, stmt, filters: TicketListFilters):
        if filters.status:
            stmt = stmt.where(Ticket.status == filters.status)
        if filters.severity:
            stmt = stmt.where(Ticket.severity == filters.severity)
        if filters.priority:
            stmt = stmt.where(Ticket.priority == filters.priority)
        if filters.customer_id:
            stmt = stmt.where(Ticket.customer_id == filters.customer_id)
        if filters.assignee_id:
            stmt = stmt.where(Ticket.assignee_id == filters.assignee_id)
        if filters.is_breached is not None:
            stmt = stmt.where(Ticket.is_breached == filters.is_breached)
        if filters.is_escalated is not None:
            stmt = stmt.where(Ticket.is_escalated == filters.is_escalated)
        return stmt

    async def _paginate(
        self, stmt, filters: TicketListFilters
    ) -> tuple[int, list[Ticket]]:
        count_result = await self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar_one()

        stmt = stmt.order_by(Ticket.created_at.desc())
        stmt = stmt.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)

        result = await self.db.execute(stmt)
        return total, list(result.scalars().all())