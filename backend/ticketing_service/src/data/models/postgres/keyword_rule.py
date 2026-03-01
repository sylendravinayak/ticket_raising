import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from src.data.models.postgres.base import Base
from src.constants.enum import Priority, Severity


class KeywordRule(Base):
    __tablename__ = "keyword_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    keywords: Mapped[list] = mapped_column(JSON, nullable=False)  
    priority: Mapped[Priority] = mapped_column(SAEnum(Priority), nullable=False)
    severity: Mapped[Severity] = mapped_column(SAEnum(Severity), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )