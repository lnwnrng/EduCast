"""OpenAI 兼容 chat/completions LLM Provider 基类。

OpenAI / DeepSeek / 智谱 GLM 均采用 OpenAI 兼容端点：

    POST {base_url}/chat/completions
    Authorization: Bearer <api_key>
    body: {model, messages, temperature, max_tokens, response_format?}
    resp: choices[0].message.content / usage.{prompt,completion}_tokens

差异点由子类通过 `provider_type` / `supports_thinking` 控制：
- OpenAI 新型号用 `max_completion_tokens`；GLM/DeepSeek 用 `max_tokens`。
- GLM/DeepSeek 为混合思考模型，`thinking_disabled=True` 时注入
  `thinking: {"type": "disabled"}` 以稳定结构化输出。
"""

import logging
import uuid
from typing import Any

from app.providers.base import ProviderResult
from app.providers.llm._httpx import get_shared_httpx_client
from app.providers.llm.base_llm import LLMProviderBase

logger = logging.getLogger(__name__)


class OpenAICompatibleLLMProvider(LLMProviderBase):
    """OpenAI 兼容端点的 LLM Provider 基类。"""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        *,
        provider_type: str,
        provider_name: str,
        supports_thinking: bool = False,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._provider_type = provider_type
        self._provider_name = provider_name
        self._supports_thinking = supports_thinking

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.6,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
        thinking_disabled: bool = True,
    ) -> ProviderResult:
        """调用 chat/completions，返回带 content 的 ProviderResult。"""
        url = f"{self._base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        # OpenAI 新型号（含 o 系列 / gpt-4.1 / gpt-4o）统一用 max_completion_tokens；
        # GLM/DeepSeek 用 max_tokens。
        if self._provider_type == "openai":
            payload["max_completion_tokens"] = max_tokens
        else:
            payload["max_tokens"] = max_tokens

        if self._supports_thinking and thinking_disabled:
            payload["thinking"] = {"type": "disabled"}
        if response_format is not None:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        client = get_shared_httpx_client(timeout=self._timeout)
        resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code != 200:
            raise RuntimeError(
                f"{self._provider_name} API 返回 {resp.status_code}: {resp.text[:500]}"
            )

        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"{self._provider_name} API 响应缺少 choices: {data}")

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
