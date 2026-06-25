"""视频生成 Provider 配置 Schema。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class VideoGenProviderConfigCreate(BaseModel):
    """创建视频生成 provider 配置。"""

    provider_type: str = Field(..., description="cogvideox | kling | minimax")
    name: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(..., min_length=1, max_length=255)
    base_url: str = Field(default="", max_length=255)
    model_id: str = Field(default="", max_length=100)
    is_enabled: bool = True
    is_active: bool = False
    sort_order: int = 0


class VideoGenProviderConfigUpdate(BaseModel):
    """更新视频生成 provider 配置 — 全字段可选；api_key 留空表示不变。"""

    name: str | None = Field(default=None, max_length=100)
    api_key: str | None = Field(default=None, max_length=255)
    base_url: str | None = Field(default=None, max_length=255)
    model_id: str | None = Field(default=None, max_length=100)
    is_enabled: bool | None = None
    sort_order: int | None = None


class VideoGenProviderConfigResponse(BaseModel):
    """视频生成 provider 配置响应（api_key 脱敏）。"""

    model_config = {"from_attributes": True}

    id: UUID
    provider_type: str
    name: str
    base_url: str
    model_id: str
    is_enabled: bool
    is_active: bool
    sort_order: int
    api_key_masked: str = ""
    is_configured: bool = True
    created_at: datetime
    updated_at: datetime | None = None


class VideoGenTestResult(BaseModel):
    """视频生成 provider 连通性测试结果。"""

    ok: bool
    message: str
