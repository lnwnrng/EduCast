"""视频标注模型 — 时间线批注与知识点标记。"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class Annotation(BaseMixin, Base):
    """视频时间线标注 — 教师在视频时间线上添加的文字批注。

    支持:
    - 时间戳定位（秒）
    - 文字批注
    - 知识点关联
    - 颜色标记
    """

    __tablename__ = "annotations"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True,
    )
    timestamp: Mapped[float] = mapped_column(Float, default=0.0)
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    text: Mapped[str] = mapped_column(Text)
    annotation_type: Mapped[str] = mapped_column(
        String(20), default="note",
    )
    color: Mapped[str] = mapped_column(String(20), default="#1890ff")
    scene_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    knowledge_point_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # ── 关系 ─────────────────────────────────────────────
    project: Mapped["Project"] = relationship(back_populates="annotations")
