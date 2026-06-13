"""课程分类模型（树形结构）。"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from app.models.project import Project


class CourseCategory(BaseMixin, Base):
    """课程分类 — 支持无限级树形结构。"""

    __tablename__ = "course_categories"

    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("course_categories.id"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # ── 关系 ─────────────────────────────────────────────
    children: Mapped[list["CourseCategory"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    parent: Mapped["CourseCategory | None"] = relationship(
        back_populates="children", remote_side="CourseCategory.id"
    )
    projects: Mapped[list["Project"]] = relationship(back_populates="category")
