from typing import Generic, TypeVar, Type, Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, asc, desc
from sqlalchemy.sql import Select
from pydantic import BaseModel

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model


    def get(self, db: Session, obj_id: Any) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.id == obj_id)
        return db.scalar(stmt)

    def create(self, db: Session, obj_in: CreateSchemaType) -> ModelType:
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        db_obj: ModelType,
        obj_in: UpdateSchemaType
    ) -> ModelType:
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, obj_id: Any) -> None:
        stmt = select(self.model).where(self.model.id == obj_id)
        db_obj = db.scalar(stmt)

        if not db_obj:
            return

        db.delete(db_obj)
        db.commit()


    def list(
        self,
        db: Session,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 20,
        allowed_filter_fields: Optional[List[str]] = None,
        allowed_sort_fields: Optional[List[str]] = None,
    ) -> Tuple[List[ModelType], int]:

        stmt: Select = select(self.model)

        if filters:
            for field, value in filters.items():
                if allowed_filter_fields and field not in allowed_filter_fields:
                    continue

                column = getattr(self.model, field, None)
                if column is not None:
                    stmt = stmt.where(column == value)

        if sort_by:
            if allowed_sort_fields and sort_by not in allowed_sort_fields:
                sort_by = None

        if sort_by:
            column = getattr(self.model, sort_by, None)
            if column is not None:
                if sort_order.lower() == "desc":
                    stmt = stmt.order_by(desc(column))
                else:
                    stmt = stmt.order_by(asc(column))

        total = db.scalar(select(self.model).count())

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        results = db.scalars(stmt).all()

        return results, total