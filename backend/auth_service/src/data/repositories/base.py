from typing import Generic, TypeVar, Type
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.data.models.postgres.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
  

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id: UUID) -> ModelType | None:
        """Fetch entity by primary key."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)  
        )
        return result.scalar_one_or_none()

    async def save(self, instance: ModelType) -> ModelType:
        """Persist new or updated entity."""
        self.session.add(instance)
        await self.session.flush()  
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Remove entity from DB."""
        await self.session.delete(instance)
        await self.session.flush()