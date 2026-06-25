"""LLM Provider 抽象基类 — 在 BaseProvider 之上增加 `chat()` 同步语义。

统一接口 submit→poll→get_result 是为长任务（视频生成/数字人）设计的，
对 LLM 这类同步请求/响应能力而言偏重。本类把 `chat()` 固化为 LLM 的主
要入口，并在此实现 submit/poll/get_result/estimate_cost 的内存缓存样板，
子类只需实现 `chat()`。
"""

import abc
from typing import Any

from app.providers.base import BaseProvider, ProviderResult


class LLMProviderBase(BaseProvider, abc.ABC):
    """LLM Provider 基类。

    子类实现 `chat()` 即可；`submit`/`poll`/`get_result` 在此用内存缓存桥接
    统一 Provider 接口。
    """

    def __init__(self, *, timeout: float = 60.0) -> None:
        self._timeout = timeout
        # submit/get_result 之间缓存结果（带 TTL 淘汰，防止内存泄漏）
        self._results: dict[str, ProviderResult] = {}
        self._results_order: list[str] = []
        self._max_cache_size = 100

    @abc.abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.6,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
        thinking_disabled: bool = True,
    ) -> ProviderResult:
        """调用 LLM，返回带 content 的 ProviderResult。

        Args:
            messages: OpenAI 风格消息列表 [{"role","content"}]，
                role 可含 system（Claude provider 会将其提升为顶层 system）。
            temperature: 采样温度。
            max_tokens: 最大输出 token。
            response_format: 如 {"type": "json_object"} 要求 JSON 输出。
            thinking_disabled: 混合思考模型默认关闭推理以稳定结构化输出。

        Raises:
            httpx.HTTPError / RuntimeError: 网络异常或非 2xx 响应，交由上层降级。
        """
        ...

    async def submit(self, request: dict) -> str:
        """提交 LLM 生成请求，缓存结果并返回 task_id。"""
        result = await self.chat(
            messages=request["messages"],
            temperature=request.get("temperature", 0.6),
            max_tokens=request.get("max_tokens", 4096),
            response_format=request.get("response_format"),
            thinking_disabled=request.get("thinking_disabled", True),
        )
        self._cache_result(result)
        return result.task_id

    def _cache_result(self, result: ProviderResult) -> None:
        """缓存结果并淘汰超出上限的旧条目。"""
        self._results[result.task_id] = result
        self._results_order.append(result.task_id)
        while len(self._results_order) > self._max_cache_size:
            old_id = self._results_order.pop(0)
            self._results.pop(old_id, None)

    async def poll(self, task_id: str) -> ProviderResult:
        """轮询任务状态（LLM 为同步调用，直接返回缓存结果）。"""
        return await self.get_result(task_id)

    async def get_result(self, task_id: str) -> ProviderResult:
        """获取生成结果。"""
        result = self._results.get(task_id)
        if result is None:
            return ProviderResult(
                task_id=task_id,
                status="failed",
                error_msg=f"未找到任务 {task_id} 的结果",
            )
        return result

    def estimate_cost(self, request: dict) -> float:
        """成本预估 — 默认 0（免费档 / 未接入计费）。子类可覆盖。"""
        return 0.0
