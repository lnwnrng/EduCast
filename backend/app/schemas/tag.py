"""标签 Pydantic 模型。"""

from datetime import datetime

from pydantic import BaseModel


class TagResponse(BaseModel):
    id: str
    name: str
    color: str = "#1677ff"
    project_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str
    color: str = "#1677ff"


class TagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None