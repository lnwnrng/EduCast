"""用户 Pydantic 模型。"""

from datetime import datetime

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """用户公开信息（响应）。"""

    id: str
    username: str
    role: str
    is_active: bool
    last_login: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserAdminResponse(UserResponse):
    """管理员视角的用户信息，包含更新时间。"""

    updated_at: datetime | None = None
    project_count: int = 0