import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from src.data.models.postgres.base import Base


class EscalationHistory(Base):
    __tablename__ = "escalation_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    escalated_to_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    escalated_to_lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    escalated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )