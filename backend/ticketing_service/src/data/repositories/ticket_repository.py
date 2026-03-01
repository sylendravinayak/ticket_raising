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

    # ──────────────────────────────────────────
    # READ
    # ──────────────────────────────────────────

    async def get_by_id(self, ticket_id: int, eager: bool = False) -> Optional[Ticket]:
        stmt = select(Ticket).where(Ticket.ticket_id == ticket_id)
        if eager:
            stmt = stmt.options(*_EAGER)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_number(self, ticket_number: str) -> Optional[Ticket]:
        result = await self.db.execute(
            select(Ticket).where(Ticket.ticket_number == ticket_number)
        )
        return result.scalar_one_or_none()

    async def next_ticket_number(self) -> str:
        """
        Generates TKT-XXXX.
        Uses COUNT + 1 for simplicity; safe under a DB-level unique constraint.
        """
        result = await self.db.execute(select(func.count(Ticket.ticket_id)))
        count = result.scalar_one()
        return f"TKT-{count + 1:04d}"

    async def list_for_customer(
        self, customer_id: int, filters: TicketListFilters
    ) -> tuple[int, list[Ticket]]:
        stmt = select(Ticket).where(Ticket.customer_id == customer_id)
        stmt = self._apply_filters(stmt, filters)
        return await self._paginate(stmt, filters)

    async def list_all(
        self, filters: TicketListFilters
    ) -> tuple[int, list[Ticket]]:
        stmt = select(Ticket)
        stmt = self._apply_filters(stmt, filters)
        return await self._paginate(stmt, filters)

    async def get_breachable(self, now: datetime) -> list[Ticket]:
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.resolution_due_at < now,
                Ticket.status.not_in([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
                Ticket.is_breached == False,
            )
        )
        return list(result.scalars().all())

    async def get_escalatable(self, now: datetime) -> list[Ticket]:
        """
        Breached tickets not yet escalated, still open.
        Escalation timing is evaluated inside the service using SLARule.escalation_after_minutes.
        """
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.is_breached == True,
                Ticket.is_escalated == False,
                Ticket.status.not_in([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            )
        )
        return list(result.scalars().all())

    async def get_auto_closeable(self, cutoff: datetime) -> list[Ticket]:
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.status == TicketStatus.RESOLVED,
                Ticket.resolved_at <= cutoff,
            )
        )
        return list(result.scalars().all())

    async def get_events(self, ticket_id: int) -> list[TicketEvent]:
        result = await self.db.execute(
            select(TicketEvent)
            .where(TicketEvent.ticket_id == ticket_id)
            .order_by(TicketEvent.created_at.desc())
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────
    # WRITE
    # ──────────────────────────────────────────

    async def create(self, ticket: Ticket) -> Ticket:
        self.db.add(ticket)
        await self.db.flush()
        await self.db.refresh(ticket)
        return ticket

    async def save(self, ticket: Ticket) -> Ticket:
        self.db.add(ticket)
        await self.db.flush()
        await self.db.refresh(ticket)
        return ticket

    async def add_event(self, event: TicketEvent) -> TicketEvent:
        self.db.add(event)
        await self.db.flush()
        return event

    async def add_comment(self, comment: TicketComment) -> TicketComment:
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)
        return comment

    async def add_attachment(self, attachment: TicketAttachment) -> TicketAttachment:
        self.db.add(attachment)
        await self.db.flush()
        return attachment

    async def add_notification_log(self, log: NotificationLog) -> NotificationLog:
        self.db.add(log)
        await self.db.flush()
        return log

    async def add_escalation(self, esc: EscalationHistory) -> EscalationHistory:
        self.db.add(esc)
        await self.db.flush()
        return esc

    # ──────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────

    @staticmethod
    def _apply_filters(stmt, filters: TicketListFilters):
        if filters.status:
            stmt = stmt.where(Ticket.status == filters.status)
        if filters.severity:
            stmt = stmt.where(Ticket.severity == filters.severity)
        if filters.priority:
            stmt = stmt.where(Ticket.priority == filters.priority)
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

        offset = (filters.page - 1) * filters.page_size
        result = await self.db.execute(
            stmt.order_by(Ticket.created_at.desc())
            .offset(offset)
            .limit(filters.page_size)
        )
        return total, list(result.scalars().all())