"""分类/标签申请模型。"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseMixin


class CategoryTagRequest(BaseMixin, Base):
    """分类/标签申请 — 普通用户提交，管理员审核。"""

    __tablename__ = "category_tag_requests"

    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(16))  # "category" or "tag"
    reason: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(
        String(16), default="pending"
    )  # pending/approved/rejected
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
