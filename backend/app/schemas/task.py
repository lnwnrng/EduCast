"""任务 Schema。"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """创建任务请求。"""

    task_type: str = Field(default="full_pipeline", description="任务类型")
    config: dict[str, Any] | None = Field(default=None, description="生成配置")


class TaskResponse(BaseModel):
    """任务响应。"""

    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    task_type: str
    status: str
    progress: int
    error_message: str | None = None
    estimated_cost: float
    actual_cost: float
    created_at: datetime
    updated_at: datetime | None = None


class TaskStatusResponse(BaseModel):
    """任务状态简要响应。"""

    id: UUID
    status: str
    progress: int
    error_message: str | None = None
    estimated_cost: float
    actual_cost: float


class SubTaskResponse(BaseModel):
    """子任务响应。"""

    model_config = {"from_attributes": True}

    id: UUID
    task_id: UUID
    subtask_type: str
    scene_id: str | None = None
    status: str
    progress: int
    provider_name: str | None = None
    result_url: str | None = None
    cost: float
    retry_count: int
    error_message: str | None = None
    created_at: datetime
