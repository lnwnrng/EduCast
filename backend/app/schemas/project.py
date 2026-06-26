"""项目 Schema。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.tag import TagResponse


class ProjectCreate(BaseModel):
    """创建项目请求。"""

    title: str = Field(..., min_length=1, max_length=255, description="项目标题")
    subject: str = Field(default="", max_length=100, description="学科")
    grade: str = Field(default="", max_length=50, description="年级")
    description: str | None = Field(default=None, description="描述")
    template: str = Field(default="micro_lecture", description="视频模板")
    tag_ids: list[str] = Field(default_factory=list, description="标签ID列表")


class ProjectUpdate(BaseModel):
    """更新项目请求 — 所有字段可选。"""

    title: str | None = Field(default=None, max_length=255)
    subject: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=50)
    description: str | None = None
    template: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=20)
    tag_ids: list[str] | None = None


class ProjectResponse(BaseModel):
    """项目响应。"""

    model_config = {"from_attributes": True}

    id: UUID
    title: str
    subject: str
    grade: str
    description: str | None = None
    template: str
    status: str
    tags: list[TagResponse] = []
    created_at: datetime
    updated_at: datetime | None = None
