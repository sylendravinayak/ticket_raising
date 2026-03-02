"""SLA, SLARule, and SLAPolicy repository."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.constants.enum import Priority, Severity
from src.data.models.postgres.sla import SLA, SLARule


class SLARepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active_sla_for_tier(self, customer_tier_id: int) -> Optional[SLA]:
        result = await self.db.execute(
            select(SLA)
            .where(
                SLA.customer_tier_id == customer_tier_id,
                SLA.is_active == True,
            )
            .options(selectinload(SLA.rules))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_rule(
        self,
        sla_id: int,
        severity: Severity,
        priority: Priority,
    ) -> Optional[SLARule]:
        result = await self.db.execute(
            select(SLARule).where(
                SLARule.sla_id == sla_id,
                SLARule.severity == severity,
                SLARule.priority == priority,
            )
        )
        return result.scalar_one_or_none()

    async def get_sla_by_id(self, sla_id: int) -> Optional[SLA]:
        result = await self.db.execute(
            select(SLA)
            .where(SLA.sla_id == sla_id)
            .options(selectinload(SLA.rules))
        )
        return result.scalar_one_or_none()