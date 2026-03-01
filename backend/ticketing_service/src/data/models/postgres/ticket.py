import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Text, Boolean, DateTime, ForeignKey,
    Enum as SAEnum, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from src.data.models.postgres import Base
from src.constants.enum import TicketStatus, Priority, Severity, Channel


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    product: Mapped[Optional[str]] = mapped_column(String(200))
    area_of_concern: Mapped[Optional[str]] = mapped_column(String(200))

    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus), default=TicketStatus.NEW, nullable=False
    )
    priority: Mapped[Priority] = mapped_column(
        SAEnum(Priority), default=Priority.MEDIUM, nullable=False
    )
    severity: Mapped[Severity] = mapped_column(
        SAEnum(Severity), default=Severity.S3, nullable=False
    )
    channel: Mapped[Channel] = mapped_column(SAEnum(Channel), nullable=False)

    # Actors
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assigned_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # SLA
    sla_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    response_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolution_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False)
    is_escalated: Mapped[bool] = mapped_column(Boolean, default=False)

    email_thread_id: Mapped[Optional[str]] = mapped_column(String(500))
    email_message_id: Mapped[Optional[str]] = mapped_column(String(500))

    priority_override_justification: Mapped[Optional[str]] = mapped_column(Text)
    priority_overridden_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    attachments: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow,
        onupdate=datetime.utcnow, nullable=False
    )

    
    events: Mapped[list["TicketEvent"]] = relationship(
        "TicketEvent", back_populates="ticket", cascade="all, delete-orphan"
    )
    comments: Mapped[list["TicketComment"]] = relationship(
        "TicketComment", back_populates="ticket", cascade="all, delete-orphan"
    )