"""项目工作台聚合 Schema。"""

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.cost import CostEstimate


class VideoVersion(BaseModel):
    """一个成片版本（一次生成）。"""

    version: int
    ir_version: int | None = None
    resource_id: UUID
    subtitle_vtt_id: UUID | None = None
    archive_id: UUID | None = None
    created_at: str | None = None


class LatestTask(BaseModel):
    """最近一次任务的简要状态。"""

    id: UUID
    status: str
    progress: int
    step_detail: str | None = None
    error_message: str | None = None


class WorkspaceResponse(BaseModel):
    """工作台一次渲染所需的聚合数据。"""

    project_id: UUID
    title: str
    status: str
    subject: str = ""
    grade: str = ""
    has_ir: bool = False
    latest_ir_version: int | None = None
    videos: list[VideoVersion] = Field(default_factory=list)
    is_stale: bool = False
    cost_estimate: CostEstimate | None = None
    latest_task: LatestTask | None = None
