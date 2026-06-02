"""ZhipuLLMProvider 测试 — 用 httpx.MockTransport 拦截请求，不打真实 API。"""

import json

import httpx
import pytest

import app.providers.llm.zhipu as zhipu_mod
from app.providers.llm.zhipu import ZhipuLLMProvider

pytestmark = pytest.mark.asyncio


def _patch_transport(monkeypatch, handler) -> None:
    """把 zhipu 模块内的 httpx.AsyncClient 替换为带 MockTransport 的版本。"""
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def make_client(**kwargs):
        kwargs.pop("transport", None)
        return real_client(transport=transport, **kwargs)

    monkeypatch.setattr(zhipu_mod.httpx, "AsyncClient", make_client)


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
