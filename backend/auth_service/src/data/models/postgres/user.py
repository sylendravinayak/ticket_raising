from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    String,
    Boolean,
    ForeignKey,
    Index,
    Enum,
    text,
)
from uuid import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.models.postgres.base import Base, TimestampMixin, UUIDMixin

# if TYPE_CHECKING:
from src.data.models.postgres.token import RefreshToken
from src.data.models.postgres.role import Role


class ContactMode(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    
    lead_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    preferred_mode_of_contact: Mapped[ContactMode] = mapped_column(
        Enum(ContactMode, name="contact_mode_enum"),
        nullable=False,
        server_default="email",
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    role: Mapped["Role"] = relationship(
        back_populates="users",
        lazy="joined",
    )

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"