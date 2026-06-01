"""项目（课程）模型。"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from app.models.resource import Resource
    from app.models.task import Task


class Project(BaseMixin, Base):
    """课程项目 — 一个项目对应一门课程的视频生产。"""

    __tablename__ = "projects"

    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(100), default="")
    grade: Mapped[str] = mapped_column(String(50), default="")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    template: Mapped[str] = mapped_column(String(50), default="micro_lecture")
    status: Mapped[str] = mapped_column(String(20), default="draft")

    # ── 关系 ─────────────────────────────────────────────
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    resources: Mapped[list["Resource"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
