"""
Ticket repository — all DB access via SQLAlchemy ORM, no raw SQL.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.constants.enum import TicketStatus
from src.data.models.postgres.escalation import EscalationHistory
from src.data.models.postgres.notification_log import NotificationLog
from src.data.models.postgres.ticket import Ticket
from src.data.models.postgres.ticket_attachment import TicketAttachment
from src.data.models.postgres.ticket_comment import TicketComment
from src.data.models.postgres.ticket_event import TicketEvent
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

    async def add_event(self, event: TicketEvent) -> None:
        self.db.add(event)
        await self.db.flush()

    async def add_attachment(self, attachment: TicketAttachment) -> None:
        self.db.add(attachment)
        await self.db.flush()

    async def add_comment(self, comment: TicketComment) -> None:
        self.db.add(comment)
        await self.db.flush()

    async def add_escalation(self, escalation: EscalationHistory) -> None:
        self.db.add(escalation)
        await self.db.flush()

    async def add_notification_log(self, log: NotificationLog) -> None:
        self.db.add(log)
        await self.db.flush()

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