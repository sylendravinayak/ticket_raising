"""KeywordRule repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.keyword_rule import KeywordRule


class KeywordRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active_rules(self) -> list[KeywordRule]:
        result = await self.db.execute(
            select(KeywordRule)
            .where(KeywordRule.is_active == True)
            .order_by(KeywordRule.keyword_rule_id)
        )
        return list(result.scalars().all())