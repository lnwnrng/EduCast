"""分类 Pydantic 模型。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CategoryBrief(BaseModel):
    """分类简要信息（用于嵌套在项目响应中）。"""

    id: UUID
    name: str
    parent_id: UUID | None = None

    model_config = {"from_attributes": True}


class CategoryNode(BaseModel):
    """分类节点（含子节点递归）。"""

    id: UUID
    name: str
    parent_id: UUID | None = None
    sort_order: int = 0
    children: list["CategoryNode"] = []
    project_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str
    parent_id: UUID | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = None
    parent_id: UUID | None = None
    sort_order: int | None = None
