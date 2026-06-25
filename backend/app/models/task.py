"""任务与子任务模型。"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from app.models.project import Project


class Task(BaseMixin, Base):
    """视频生成任务 — 对应一次完整的流水线执行。

    状态机: pending → parsing → scripting → reviewing → generating
            → composing → completed / failed
    """

    __tablename__ = "tasks"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"),
        index=True,
    )
    task_type: Mapped[str] = mapped_column(String(50), default="full_pipeline")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    ir_snapshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    actual_cost: Mapped[float] = mapped_column(Float, default=0.0)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── 关系 ─────────────────────────────────────────────
    project: Mapped["Project"] = relationship(back_populates="tasks")
    subtasks: Mapped[list["SubTask"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )


class SubTask(BaseMixin, Base):
    """并行子任务 — 生成阶段的最小执行单元。

    subtask_type: tts / render / digital_human / video_gen / formula_anim
    """

    __tablename__ = "sub_tasks"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id"),
    )
    subtask_type: Mapped[str] = mapped_column(String(50))
    scene_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    provider_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_task_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    result_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── 关系 ─────────────────────────────────────────────
    task: Mapped["Task"] = relationship(back_populates="subtasks")
