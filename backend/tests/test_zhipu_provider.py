"""ZhipuLLMProvider 测试 — 用 httpx.MockTransport 拦截请求，不打真实 API。

GLM provider 的 chat 实现位于 OpenAICompatibleLLMProvider，通过共享
httpx 客户端（app.providers.llm._httpx.get_shared_httpx_client）发请求。
本测试 patch 该客户端工厂，注入带 MockTransport 的客户端。
"""

import json

import httpx
import pytest

from app.providers.llm.zhipu import ZhipuLLMProvider

pytestmark = pytest.mark.asyncio


def _patch_transport(monkeypatch, handler) -> None:
    """把 openai_compat 模块引用的共享 httpx 客户端工厂替换为 MockTransport 版本。"""
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)

    monkeypatch.setattr(
        "app.providers.llm.openai_compat.get_shared_httpx_client",
        lambda timeout=60.0: client,
    )


async def test_chat_builds_payload_and_parses(monkeypatch) -> None:
    """验证请求 payload（model/thinking/auth）与响应解析。"""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "你好世界"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 7},
            },
        )

    _patch_transport(monkeypatch, handler)

    provider = ZhipuLLMProvider(api_key="testkey", model="glm-4.7-flash")
    result = await provider.chat(
        [{"role": "user", "content": "hi"}],
        response_format={"type": "json_object"},
    )

    assert captured["url"].endswith("/chat/completions")
    assert captured["auth"] == "Bearer testkey"
    assert captured["body"]["model"] == "glm-4.7-flash"
    assert captured["body"]["thinking"] == {"type": "disabled"}
    assert captured["body"]["response_format"] == {"type": "json_object"}
    # GLM 走 max_tokens（非 openai 的 max_completion_tokens）
    assert captured["body"]["max_tokens"] == 4096

    assert result.content == "你好世界"
    assert result.status == "completed"
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 7
    assert result.cost == 0.0


async def test_chat_non_200_raises(monkeypatch) -> None:
    """非 200 响应抛出 RuntimeError，交由上层降级。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    _patch_transport(monkeypatch, handler)

    provider = ZhipuLLMProvider(api_key="testkey")
    with pytest.raises(RuntimeError):
        await provider.chat([{"role": "user", "content": "hi"}])


async def test_submit_get_result_roundtrip(monkeypatch) -> None:
    """submit 缓存结果，get_result 取回（统一 Provider 接口）。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "OK"}}]},
        )

    _patch_transport(monkeypatch, handler)

    provider = ZhipuLLMProvider(api_key="testkey")
    task_id = await provider.submit({"messages": [{"role": "user", "content": "hi"}]})
    result = await provider.get_result(task_id)
    assert result.content == "OK"
    assert provider.estimate_cost({}) == 0.0
