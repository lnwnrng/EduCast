"""标签模型。"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseMixin


class Tag(BaseMixin, Base):
    """标签 — 自由打标。"""

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(50), unique=True)
    color: Mapped[str] = mapped_column(String(7), default="#1677ff")