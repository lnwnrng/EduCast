"""资源 Schema。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ResourceResponse(BaseModel):
    """资源响应。"""

    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    resource_type: str
    title: str
    name: str = ""
    file_path: str
    file_size: int
    mime_type: str | None = None
    version: int
    is_folder: bool = False
    parent_id: UUID | None = None
    watermark_applied: bool
    created_at: datetime
    updated_at: datetime | None = None


class FolderCreate(BaseModel):
    """新建子文件夹。"""

    project_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: UUID | None = None


class ResourcePatch(BaseModel):
    """重命名 / 移动资源（字段可选；parent_id 显式 null = 移回项目根）。"""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: UUID | None = None
