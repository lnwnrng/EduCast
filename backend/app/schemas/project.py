"""项目 Schema。"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """创建项目请求。"""

    title: str = Field(..., min_length=1, max_length=255, description="项目标题")
    subject: str = Field(default="", max_length=100, description="学科")
    grade: str = Field(default="", max_length=50, description="年级")
    description: Optional[str] = Field(default=None, description="描述")
    template: str = Field(default="micro_lecture", description="视频模板")


class ProjectUpdate(BaseModel):
    """更新项目请求 — 所有字段可选。"""

    title: Optional[str] = Field(default=None, max_length=255)
    subject: Optional[str] = Field(default=None, max_length=100)
    grade: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    template: Optional[str] = Field(default=None, max_length=50)
    status: Optional[str] = Field(default=None, max_length=20)


class ProjectResponse(BaseModel):
    """项目响应。"""

    model_config = {"from_attributes": True}

    id: UUID
    title: str
    subject: str
    grade: str
    description: Optional[str] = None
    template: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
