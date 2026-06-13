"""用户模型。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from app.models.project import Project


class User(BaseMixin, Base):
    """用户账号。"""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(16), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── 关系 ─────────────────────────────────────────────
    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
