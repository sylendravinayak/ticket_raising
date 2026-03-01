import uuid
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.data.models.postgres.ticket import Ticket
from src.data.models.postgres.ticket_event import TicketEvent
from src.constants.enum import TicketStatus, EventType


class TicketRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, ticket_id: uuid.UUID) -> Optional[Ticket]:
        result = await self.db.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.events),
                selectinload(Ticket.comments),
            )
            .where(Ticket.id == ticket_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email_thread_id(self, thread_id: str) -> Optional[Ticket]:
        result = await self.db.execute(
            select(Ticket).where(Ticket.email_thread_id == thread_id)
        )
        return result.scalar_one_or_none()

    async def get_by_customer_id(self, customer_id: uuid.UUID) -> list[Ticket]:
        result = await self.db.execute(
            select(Ticket)
            .where(Ticket.customer_id == customer_id)
            .order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_agent_id(self, agent_id: uuid.UUID) -> list[Ticket]:
        result = await self.db.execute(
            select(Ticket)
            .where(Ticket.assigned_agent_id == agent_id)
            .order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_tickets(self) -> list[Ticket]:
        result = await self.db.execute(
            select(Ticket).where(Ticket.status != TicketStatus.CLOSED)
        )
        return list(result.scalars().all())

    async def save(self, ticket: Ticket) -> Ticket:
        self.db.add(ticket)
        await self.db.flush()  # flush to get ID without committing
        await self.db.refresh(ticket)
        return ticket

    async def log_event(
        self,
        ticket_id: uuid.UUID,
        event_type: EventType,
        metadata: dict,
        actor_id: Optional[uuid.UUID],
        actor_role: Optional[str],
    ) -> TicketEvent:
        event = TicketEvent(
            ticket_id=ticket_id,
            event_type=event_type,
            metadata_=metadata,
            actor_id=actor_id,
            actor_role=actor_role,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def get_events(self, ticket_id: uuid.UUID) -> list[TicketEvent]:
        result = await self.db.execute(
            select(TicketEvent)
            .where(TicketEvent.ticket_id == ticket_id)
            .order_by(TicketEvent.created_at.asc())
        )
        return list(result.scalars().all())