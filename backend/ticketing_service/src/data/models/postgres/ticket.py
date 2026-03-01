from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum as SAEnum,
    ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.constants.enum import (
    Environment, Priority, Severity, TicketSource, TicketStatus,
)
from src.data.models.postgres.base import Base

if TYPE_CHECKING:
    from src.data.models.postgres.sla import SLA
    from src.data.models.postgres.ticket_attachment import TicketAttachment
    from src.data.models.postgres.ticket_comment import TicketComment
    from src.data.models.postgres.ticket_event import TicketEvent
    from src.data.models.postgres.email_thread import EmailThread
    from src.data.models.postgres.escalation import EscalationHistory
    from src.data.models.postgres.notification_log import NotificationLog


class Ticket(Base):

    __tablename__ = "tickets"

    ticket_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticket_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    product: Mapped[str] = mapped_column(String(100), nullable=False)
    environment: Mapped[Environment] = mapped_column(
        SAEnum(Environment, name="environment_enum", create_type=True), nullable=False
    )
    area_of_concern: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    source: Mapped[TicketSource] = mapped_column(
        SAEnum(TicketSource, name="ticket_source_enum", create_type=True),
        nullable=False,
        default=TicketSource.UI,
    )
    severity: Mapped[Severity] = mapped_column(
        SAEnum(Severity, name="severity_enum", create_type=True), nullable=False
    )
    priority: Mapped[Priority] = mapped_column(
        SAEnum(Priority, name="priority_enum", create_type=True), nullable=False
    )
    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status_enum", create_type=True),
        nullable=False,
        default=TicketStatus.NEW,
    )

    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    assignee_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
  
    sla_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("slas.sla_id", ondelete="SET NULL"), nullable=True
    )

    customer_tier_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("customer_tiers.tier_id", ondelete="SET NULL"), nullable=True
    )

    response_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_breached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hold_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_hold_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    sla: Mapped[Optional["SLA"]] = relationship("SLA", back_populates="tickets")
    attachments: Mapped[list["TicketAttachment"]] = relationship(
        "TicketAttachment", back_populates="ticket", cascade="all, delete-orphan"
    )
    comments: Mapped[list["TicketComment"]] = relationship(
        "TicketComment", back_populates="ticket", cascade="all, delete-orphan"
    )
    events: Mapped[list["TicketEvent"]] = relationship(
        "TicketEvent", back_populates="ticket", cascade="all, delete-orphan"
    )
    email_threads: Mapped[list["EmailThread"]] = relationship(
        "EmailThread", back_populates="ticket", cascade="all, delete-orphan"
    )
    escalation_history: Mapped[list["EscalationHistory"]] = relationship(
        "EscalationHistory", back_populates="ticket", cascade="all, delete-orphan"
    )
    notification_logs: Mapped[list["NotificationLog"]] = relationship(
        "NotificationLog", back_populates="ticket", cascade="all, delete-orphan"
    )