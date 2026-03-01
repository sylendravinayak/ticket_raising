import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from src.constants.enum import CustomerTier
from src.data.models.postgres.base import Base
from src.constants import Priority, Severity, CustomerTier


class SlaPolicy(Base):
    __tablename__ = "sla_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_tier: Mapped[CustomerTier] = mapped_column(SAEnum(CustomerTier), nullable=False)
    priority: Mapped[Priority] = mapped_column(SAEnum(Priority), nullable=False)
    severity: Mapped[Severity] = mapped_column(SAEnum(Severity), nullable=False)

    response_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    escalation_after_minutes: Mapped[int] = mapped_column(Integer, default=30)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )