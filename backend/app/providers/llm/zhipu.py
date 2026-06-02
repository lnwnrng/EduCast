"""智谱 GLM-4.7-Flash LLM Provider。

GLM-4.7-Flash（2026-01 起免费，替代 GLM-4.5-Flash）是混合思考模型，
通过 OpenAI 兼容的 chat/completions 端点调用：

    POST {base_url}/chat/completions
    Authorization: Bearer <api_key>

用于脚本编排、分镜规划、出题、合规审核。免费档，成本为 0。
"""

import logging
import uuid
from typing import Any

import httpx

from app.providers.base import BaseProvider, ProviderResult

logger = logging.getLogger(__name__)


class ZhipuLLMProvider(BaseProvider):
    """智谱 GLM-4.7-Flash Provider。

    核心方法是 `chat()`（同步请求/响应）。`submit`/`get_result` 为适配
    统一 Provider 接口的薄封装：submit 执行调用并缓存结果，get_result 取回。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "glm-4.7-flash",
        base_url: str = "https://open.bigmodel.cn/api/paas/v4",
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        # submit/get_result 之间缓存结果
        self._results: dict[str, ProviderResult] = {}

    @property
    def provider_name(self) -> str:
        return "zhipu_glm4.7_flash"

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.6,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
        thinking_disabled: bool = True,
    ) -> ProviderResult:
        """调用 GLM chat/completions，返回带 content 的 ProviderResult。

        Args:
            messages: OpenAI 风格消息列表 [{"role","content"}]。
            temperature: 采样温度。
            max_tokens: 最大输出 token。
            response_format: 如 {"type": "json_object"} 要求 JSON 输出。
            thinking_disabled: GLM-4.7-Flash 为混合思考模型，默认关闭推理以
                稳定结构化输出。

        Raises:
            httpx.HTTPError / RuntimeError: 网络异常或非 2xx 响应，交由上层降级。
        """
        url = f"{self._base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if thinking_disabled:
            payload["thinking"] = {"type": "disabled"}
        if response_format is not None:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code != 200:
            raise RuntimeError(f"GLM API 返回 {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"GLM API 响应缺少 choices: {data}")

        message = choices[0].get("message", {})
        # 混合思考模型可能返回 reasoning_content，仅取最终 content
        content = message.get("content") or ""
        usage = data.get("usage") or {}

        return ProviderResult(
            task_id=str(uuid.uuid4()),
            status="completed",
            content=content,
            cost=0.0,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )

    async def submit(self, request: dict) -> str:
        """提交 LLM 生成请求。

        request 支持: messages, temperature, max_tokens, response_format,
        thinking_disabled。执行调用并缓存结果，返回 task_id。
        """
        result = await self.chat(
            messages=request["messages"],
            temperature=request.get("temperature", 0.6),
            max_tokens=request.get("max_tokens", 4096),
            response_format=request.get("response_format"),
            thinking_disabled=request.get("thinking_disabled", True),
        )
        self._results[result.task_id] = result
        return result.task_id

    async def poll(self, task_id: str) -> ProviderResult:
        """轮询任务状态（GLM 为同步调用，直接返回缓存结果）。"""
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
        """GLM-4.7-Flash 免费档，成本为 0。"""
        return 0.0
