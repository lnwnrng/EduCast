"""Anthropic Claude Messages API LLM Provider。

端点: POST {base_url}/v1/messages （默认 https://api.anthropic.com）
头: x-api-key + anthropic-version: 2023-06-01
body: {model, messages, system(顶层), max_tokens, temperature, thinking?}
resp: content[0].text / usage.{input,output}_tokens

关键差异：system 提示词必须放在顶层 `system` 字段，不能作为 messages 中
role=system 的条目。本 provider 在调用前从 messages 中抽出 system 段落
提升到顶层。混合思考（fables/opus）默认关闭以稳定结构化输出。
"""

import logging
import uuid
from typing import Any

from app.providers.base import ProviderResult
from app.providers.llm._httpx import get_shared_httpx_client
from app.providers.llm.base_llm import LLMProviderBase

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.anthropic.com"
DEFAULT_MODEL = "claude-sonnet-4-6"
ANTHROPIC_VERSION = "2023-06-01"


class ClaudeLLMProvider(LLMProviderBase):
    """Anthropic Claude Provider（Messages API）。"""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "anthropic_claude"

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.6,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
        thinking_disabled: bool = True,
    ) -> ProviderResult:
        """调用 Messages API，返回带 content 的 ProviderResult。"""
        url = f"{self._base_url}/v1/messages"

        # 抽出 system 段落（OpenAI 风格 messages 中 role=system 的条目）
        # 提升到顶层 system 字段；Anthropic 的 messages 只允许 user/assistant。
        system_parts: list[str] = []
        conv_messages: list[dict[str, str]] = []
        for m in messages:
            if m.get("role") == "system":
                content = (m.get("content") or "").strip()
                if content:
                    system_parts.append(content)
            else:
                conv_messages.append(
                    {"role": m.get("role", "user"), "content": m.get("content", "")}
                )

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": conv_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        if thinking_disabled:
            payload["thinking"] = {"type": "disabled"}
        # Anthropic 通过顶层 system 指示 JSON 输出；response_format 在此不直接
        # 转发（Anthropic 用 tools/force_json，超出毕设范围），仅在 system 中
        # 已由调用方声明 JSON 要求，此处保持兼容不报错。

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

        client = get_shared_httpx_client(timeout=self._timeout)
        resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code != 200:
            raise RuntimeError(f"Claude API 返回 {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        content_blocks = data.get("content") or []
        text_parts: list[str] = []
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text") or "")
        content = "".join(text_parts)
        usage = data.get("usage") or {}

        return ProviderResult(
            task_id=str(uuid.uuid4()),
            status="completed",
            content=content,
            cost=0.0,
            prompt_tokens=usage.get("input_tokens"),
            completion_tokens=usage.get("output_tokens"),
        )
