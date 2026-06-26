"""教学资源模型。"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from app.models.project import Project


class Resource(BaseMixin, Base):
    """教学资源 — 视频、音频、图片、字幕、IR 快照等。

    resource_type: video / audio / image / subtitle / ir_snapshot / archive
    """

    __tablename__ = "resources"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"),
        index=True,
    )
    resource_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resources.id"), nullable=True
    )
    is_folder: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    name: Mapped[str] = mapped_column(String(255), default="", server_default="")
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    watermark_applied: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── 关系 ─────────────────────────────────────────────
    project: Mapped["Project"] = relationship(back_populates="resources")
    parent: Mapped[Optional["Resource"]] = relationship(
        remote_side="Resource.id",
        backref="children",
    )
