"""分类 Pydantic 模型。"""

from datetime import datetime

from pydantic import BaseModel


class CategoryNode(BaseModel):
    """分类节点（含子节点递归）。"""

    id: str
    name: str
    parent_id: str | None = None
    sort_order: int = 0
    children: list["CategoryNode"] = []
    project_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str
    parent_id: str | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    sort_order: int | None = None