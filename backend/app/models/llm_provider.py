"""LLM Provider 配置模型 — 多模型路由（cc-switch 风格）。

存储管理员在前端配置的 LLM provider 实例（Claude / OpenAI / GLM /
DeepSeek）及其 API Key、base_url、模型型号，以及流水线各阶段到 provider
实例的指派。脚本编排时由 `providers/llm` 工厂读取本表解析出每阶段的有
序 provider 列表。
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    pass


class LLMProviderConfig(BaseMixin, Base):
    """LLM Provider 配置实例 — 一条记录对应一个可调用的 provider 账号。

    provider_type: claude | openai | glm | deepseek
    """

    __tablename__ = "llm_provider_configs"

    provider_type: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(100))
    api_key: Mapped[str] = mapped_column(String(255))
    base_url: Mapped[str] = mapped_column(String(255))
    model_id: Mapped[str] = mapped_column(String(100))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # GLM/DeepSeek 为混合思考模型，默认关闭推理以稳定结构化输出；
    # OpenAI 也保留该开关以便对 o 系列型号控制。
    thinking_disabled: Mapped[bool] = mapped_column(Boolean, default=True)


class LLMStageAssignment(BaseMixin, Base):
    """流水线阶段 → provider 配置指派。

    stage_key: default | course_metadata | outline | scene | review
    config_id 为空表示该阶段「跟随默认」。
    """

    __tablename__ = "llm_stage_assignments"

    stage_key: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    config_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("llm_provider_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
