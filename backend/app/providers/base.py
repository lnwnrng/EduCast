"""Provider 抽象基类与统一数据结构。

所有外部生成能力（LLM/TTS/数字人/视频生成）统一实现此接口，
支持路由、降级、成本核算。
"""

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, Field


class ProviderResult(BaseModel):
    """Provider 统一返回结果。"""

    task_id: str = Field(..., description="任务 ID")
    status: str = Field(
        default="pending",
        description="状态: pending | processing | completed | failed",
    )
    result_url: str | None = Field(default=None, description="产物 URL")
    content: str | None = Field(
        default=None,
        description="文本类产物（如 LLM 生成内容），区别于 result_url",
    )
    cost: float = Field(default=0.0, description="本次调用费用")
    prompt_tokens: int | None = Field(default=None, description="输入 token 数（LLM）")
    completion_tokens: int | None = Field(
        default=None, description="输出 token 数（LLM）"
    )
    error_msg: str | None = Field(default=None, description="错误信息")


class RoutingStrategy(str, Enum):
    """Provider 路由策略。"""

    FREE_FIRST = "free_first"
    COST_FIRST = "cost_first"
    QUALITY_FIRST = "quality_first"
    AVAILABLE = "available"


class BaseProvider(ABC):
    """所有 Provider 的抽象基类。

    统一接口: submit → poll → get_result
    """

    @abstractmethod
    async def submit(self, request: dict) -> str:
        """提交生成任务，返回 task_id。"""
        ...

    @abstractmethod
    async def poll(self, task_id: str) -> ProviderResult:
        """轮询任务状态。"""
        ...

    @abstractmethod
    async def get_result(self, task_id: str) -> ProviderResult:
        """获取最终结果。"""
        ...

    @abstractmethod
    def estimate_cost(self, request: dict) -> float:
        """预估本次调用成本。"""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 标识名。"""
        ...
