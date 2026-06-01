"""任务 Schema。"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """创建任务请求。"""

    task_type: str = Field(default="full_pipeline", description="任务类型")
    config: Optional[dict[str, Any]] = Field(
        default=None, description="生成配置"
    )


class TaskResponse(BaseModel):
    """任务响应。"""

    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    task_type: str
    status: str
    progress: int
    error_message: Optional[str] = None
    estimated_cost: float
    actual_cost: float
    created_at: datetime
    updated_at: Optional[datetime] = None


class TaskStatusResponse(BaseModel):
    """任务状态简要响应。"""

    id: UUID
    status: str
    progress: int
    error_message: Optional[str] = None
    estimated_cost: float
    actual_cost: float


class SubTaskResponse(BaseModel):
    """子任务响应。"""

    model_config = {"from_attributes": True}

    id: UUID
    task_id: UUID
    subtask_type: str
    scene_id: Optional[str] = None
    status: str
    progress: int
    provider_name: Optional[str] = None
    result_url: Optional[str] = None
    cost: float
    retry_count: int
    error_message: Optional[str] = None
    created_at: datetime
