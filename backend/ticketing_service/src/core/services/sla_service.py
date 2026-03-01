from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.data.models.postgres.sla_policy import SlaPolicy
from src.data.models.postgres.ticket import Ticket
from src.constants.enum import CustomerTier

from src.config import get_settings

settings = get_settings()


class SlaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def assign_sla(self, ticket: Ticket, customer_tier: CustomerTier) -> Ticket:
        result = await self.db.execute(
            select(SlaPolicy).where(
                SlaPolicy.customer_tier == customer_tier,
                SlaPolicy.priority == ticket.priority,
                SlaPolicy.severity == ticket.severity,
                SlaPolicy.is_active == True,
            )
        )
        policy = result.scalar_one_or_none()
        now = datetime.utcnow()

        if policy:
            ticket.sla_id = policy.id
            ticket.response_due_at = now + policy.response_time_minutes
            ticket.resolution_due_at = now + policy.resolution_time_minutes
        else:
            ticket.response_due_at = now + settings.DEFAULT_RESPONSE_MINUTES
            ticket.resolution_due_at = now + settings.DEFAULT_RESOLUTION_MINUTES

        return ticket

    async def restart_timer(self, ticket: Ticket, customer_tier: CustomerTier) -> Ticket:
        """Call on agent reassignment — fresh SLA timers."""
        ticket.sla_breached = False
        return await self.assign_sla(ticket, customer_tier)