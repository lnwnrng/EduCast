"""LLM Provider 配置 Schema。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ── Provider 注册表元数据（前端渲染图标 / 型号下拉用）──


class ProviderModelInfo(BaseModel):
    """单个可选型号。"""

    model_id: str
    label: str = ""


class ProviderMeta(BaseModel):
    """provider 类型静态元数据。"""

    provider_type: str
    label: str
    icon_key: str
    default_base_url: str
    default_model: str
    supports_thinking: bool = False
    models: list[ProviderModelInfo] = Field(default_factory=list)
    key_label: str = "API Key"
    key_url: str = ""


# ── 阶段 ──────────────────────────────────────────────


class StageMeta(BaseModel):
    """阶段静态元数据。"""

    stage_key: str
    label: str
    description: str = ""


# ── Provider 配置 CRUD ────────────────────────────────


class LLMProviderConfigCreate(BaseModel):
    """创建 provider 配置。"""

    provider_type: str = Field(..., description="claude | openai | glm | deepseek")
    name: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(..., min_length=1, max_length=255)
    base_url: str = Field(default="", max_length=255)
    model_id: str = Field(default="", max_length=100)
    is_enabled: bool = True
    sort_order: int = 0
    thinking_disabled: bool = True


class LLMProviderConfigUpdate(BaseModel):
    """更新 provider 配置 — 全字段可选；api_key 留空表示不变。"""

    name: str | None = Field(default=None, max_length=100)
    api_key: str | None = Field(default=None, max_length=255)
    base_url: str | None = Field(default=None, max_length=255)
    model_id: str | None = Field(default=None, max_length=100)
    is_enabled: bool | None = None
    sort_order: int | None = None
    thinking_disabled: bool | None = None


class LLMProviderConfigResponse(BaseModel):
    """provider 配置响应（api_key 脱敏）。"""

    model_config = {"from_attributes": True}

    id: UUID
    provider_type: str
    name: str
    base_url: str
    model_id: str
    is_enabled: bool
    sort_order: int
    thinking_disabled: bool
    api_key_masked: str = ""
    is_configured: bool = True
    created_at: datetime
    updated_at: datetime | None = None


# ── 阶段指派 ─────────────────────────────────────────


class LLMStageAssignmentResponse(BaseModel):
    """阶段指派响应。"""

    model_config = {"from_attributes": True}

    stage_key: str
    config_id: UUID | None = None
    config: LLMProviderConfigResponse | None = None


class LLMStageAssignmentUpdate(BaseModel):
    """单条阶段指派更新。"""

    stage_key: str
    config_id: UUID | None = None


class LLMStageAssignmentBulkUpdate(BaseModel):
    """批量更新阶段指派。"""

    assignments: list[LLMStageAssignmentUpdate]


# ── 连通性测试 ───────────────────────────────────────


class LLMTestResult(BaseModel):
    """provider 连通性测试结果。"""

    ok: bool
    message: str
