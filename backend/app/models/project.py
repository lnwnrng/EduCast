"""项目（课程）模型。"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from app.models.annotation import Annotation
    from app.models.category import CourseCategory
    from app.models.resource import Resource
    from app.models.tag import Tag
    from app.models.task import Task
    from app.models.user import User


class Project(BaseMixin, Base):
    """课程项目 — 一个项目对应一门课程的视频生产。"""

    __tablename__ = "projects"

    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(100), default="")
    grade: Mapped[str] = mapped_column(String(50), default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    template: Mapped[str] = mapped_column(String(50), default="micro_lecture")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("course_categories.id"), nullable=True, default=None
    )

    # ── 关系 ─────────────────────────────────────────────
    owner: Mapped["User"] = relationship(back_populates="projects")
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    resources: Mapped[list["Resource"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    category: Mapped["CourseCategory | None"] = relationship(back_populates="projects")
    tags: Mapped[list["Tag"]] = relationship(secondary="project_tags")
    annotations: Mapped[list["Annotation"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
