from src.data.models.postgres.base import Base, TimestampMixin, UUIDMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.constants.enum import UserRole


class Role(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "roles"

    name: Mapped[UserRole] = mapped_column(
        nullable=False,
        index=True,
        default=UserRole.USER
    )

    users: Mapped[list["User"]] = relationship("User", back_populates="role")
