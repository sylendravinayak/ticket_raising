from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.models.postgres.base import Base

if TYPE_CHECKING:
    from src.data.models.postgres.ticket import Ticket
    from src.data.models.postgres.ticket_event import TicketEvent


class TicketComment(Base):
    """
    Comments / replies on a ticket.
    user_id  →  plain Integer (Auth Service user_id, no FK).
    """

    __tablename__ = "ticket_comments"

    comment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False
    )

    # Cross-service user reference — plain Integer, no FK
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_mandatory_note: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships (intra-service)
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="comments")
    events: Mapped[list["TicketEvent"]] = relationship("TicketEvent", back_populates="comment")