"""AgentProfile repository — used for lead lookup during escalation."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.enum import UserRole
from src.data.models.postgres.agent_profile import AgentProfile


class AgentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_user_id(self, user_id: int) -> Optional[AgentProfile]:
        result = await self.db.execute(
            select(AgentProfile).where(AgentProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_available_leads(self) -> list[AgentProfile]:
        """
        Returns AgentProfiles whose Auth Service role is LEAD.
        Because role lives in Auth Service, we maintain a local role_cache column.
        For now we return all available agents and let the caller filter.
        """
        result = await self.db.execute(
            select(AgentProfile).where(AgentProfile.is_available == True)
        )
        return list(result.scalars().all())