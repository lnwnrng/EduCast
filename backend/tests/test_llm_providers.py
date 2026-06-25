"""LLM 多模型路由 — provider 单测与 resolver 解析测试。

不发起真实网络调用：用 FakeClient 替换共享 httpx 客户端，断言请求体 /
响应解析；resolver 用内存 sqlite + db_session fixture 验证阶段指派与降级。
"""

import pytest

from app.models.llm_provider import LLMProviderConfig, LLMStageAssignment
from app.providers.llm import (
    ALL_STAGE_KEYS,
    PROVIDER_REGISTRY,
    build_provider_from_config,
    get_llm_providers_for_stages,
)
from app.providers.llm.claude import ClaudeLLMProvider
from app.providers.llm.deepseek import DeepSeekLLMProvider
from app.providers.llm.openai import OpenAILLMProvider
from app.providers.llm.zhipu import ZhipuLLMProvider

# ── 测试替身 ─────────────────────────────────────────────


class _FakeResp:
    def __init__(self, status: int, data: dict, text: str = "") -> None:
        self.status_code = status
        self._data = data
        self.text = text

    def json(self) -> dict:
        return self._data


class _FakeClient:
    def __init__(self, resp: _FakeResp) -> None:
        self._resp = resp
        self.last: tuple | None = None

    async def post(self, url, json=None, headers=None):  # noqa: ANN001
        self.last = (url, json, headers)
        return self._resp


# ── provider 单测 ───────────────────────────────────────


async def test_openai_uses_max_completion_tokens(monkeypatch) -> None:
    fake = _FakeClient(
        _FakeResp(
            200,
            {
                "choices": [{"message": {"content": "hi"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2},
            },
        )
    )
    monkeypatch.setattr(
        "app.providers.llm.openai_compat.get_shared_httpx_client",
        lambda timeout=60.0: fake,
    )
    provider = OpenAILLMProvider(api_key="sk-x", model="gpt-4.1-mini")
    result = await provider.chat([{"role": "user", "content": "hi"}], max_tokens=128)

    assert result.content == "hi"
    assert result.prompt_tokens == 1 and result.completion_tokens == 2
    url, payload, headers = fake.last  # type: ignore[assignment]
    assert payload["max_completion_tokens"] == 128
    assert "max_tokens" not in payload
    assert "thinking" not in payload
    assert headers["Authorization"] == "Bearer sk-x"


async def test_glm_injects_thinking_disabled(monkeypatch) -> None:
    fake = _FakeClient(
        _FakeResp(200, {"choices": [{"message": {"content": "x"}}], "usage": {}})
    )
    monkeypatch.setattr(
        "app.providers.llm.openai_compat.get_shared_httpx_client",
        lambda timeout=60.0: fake,
    )
    provider = ZhipuLLMProvider(api_key="z", model="glm-4.7-flash")
    await provider.chat([{"role": "user", "content": "hi"}], max_tokens=10)
    _, payload, _ = fake.last  # type: ignore[assignment]
    assert payload["max_tokens"] == 10
    assert payload["thinking"] == {"type": "disabled"}


async def test_deepseek_no_thinking_when_not_disabled(monkeypatch) -> None:
    fake = _FakeClient(
        _FakeResp(200, {"choices": [{"message": {"content": "d"}}], "usage": {}})
    )
    monkeypatch.setattr(
        "app.providers.llm.openai_compat.get_shared_httpx_client",
        lambda timeout=60.0: fake,
    )
    provider = DeepSeekLLMProvider(api_key="d", model="deepseek-v4-flash")
    await provider.chat([{"role": "user", "content": "hi"}], thinking_disabled=False)
    _, payload, _ = fake.last  # type: ignore[assignment]
    assert "thinking" not in payload
    assert payload["max_tokens"] == 4096


async def test_claude_lifts_system_and_uses_x_api_key(monkeypatch) -> None:
    fake = _FakeClient(
        _FakeResp(
            200,
            {
                "content": [{"type": "text", "text": "hello"}],
                "usage": {"input_tokens": 3, "output_tokens": 4},
            },
        )
    )
    monkeypatch.setattr(
        "app.providers.llm.claude.get_shared_httpx_client",
        lambda timeout=60.0: fake,
    )
    provider = ClaudeLLMProvider(api_key="ak", model="claude-sonnet-4-6")
    result = await provider.chat(
        [
            {"role": "system", "content": "你是助手"},
            {"role": "user", "content": "hi"},
        ],
        max_tokens=64,
    )
    url, payload, headers = fake.last  # type: ignore[assignment]
    assert url.endswith("/v1/messages")
    assert headers["x-api-key"] == "ak"
    assert headers["anthropic-version"] == "2023-06-01"
    assert payload["system"] == "你是助手"
    assert all(m["role"] != "system" for m in payload["messages"])
    assert payload["thinking"] == {"type": "disabled"}
    assert payload["max_tokens"] == 64
    assert result.content == "hello"
    assert result.prompt_tokens == 3 and result.completion_tokens == 4


async def test_openai_raises_on_non_200(monkeypatch) -> None:
    fake = _FakeClient(_FakeResp(401, {}, text="unauthorized"))
    monkeypatch.setattr(
        "app.providers.llm.openai_compat.get_shared_httpx_client",
        lambda timeout=60.0: fake,
    )
    provider = OpenAILLMProvider(api_key="sk", model="gpt-4o")
    with pytest.raises(RuntimeError):
        await provider.chat([{"role": "user", "content": "hi"}])


def test_registry_covers_four_providers() -> None:
    assert set(PROVIDER_REGISTRY) == {"glm", "openai", "deepseek", "claude"}
    for meta in PROVIDER_REGISTRY.values():
        assert meta.models  # 每类至少一个可选型号


def test_build_provider_from_config_returns_right_class() -> None:
    cfg = LLMProviderConfig(
        provider_type="claude",
        name="cl",
        api_key="ak",
        base_url="https://api.anthropic.com",
        model_id="claude-sonnet-4-6",
        is_enabled=True,
        sort_order=0,
        thinking_disabled=True,
    )
    assert isinstance(build_provider_from_config(cfg), ClaudeLLMProvider)
    cfg.provider_type = "unknown"
    assert build_provider_from_config(cfg) is None


# ── resolver 解析 ───────────────────────────────────────


async def test_resolver_env_fallback(db_session, monkeypatch) -> None:
    """DB 无配置时回退 env ZHIPU_API_KEY。"""
    monkeypatch.setattr("app.providers.llm.get_effective_key", lambda k: "envkey")
    stage_map = await get_llm_providers_for_stages(db_session)
    assert set(stage_map.keys()) == set(ALL_STAGE_KEYS)
    default = stage_map["default"]
    assert len(default) == 1
    assert isinstance(default[0], ZhipuLLMProvider)


async def test_resolver_empty_when_no_config_no_env(db_session, monkeypatch) -> None:
    monkeypatch.setattr("app.providers.llm.get_effective_key", lambda k: None)
    stage_map = await get_llm_providers_for_stages(db_session)
    assert stage_map["default"] == []
    assert stage_map["outline"] == []


async def test_resolver_stage_assignment_and_fallback_order(
    db_session, monkeypatch
) -> None:
    """阶段指派优先 → default 指派 → 其余已启用 config。"""
    monkeypatch.setattr("app.providers.llm.get_effective_key", lambda k: None)
    cfg_openai = LLMProviderConfig(
        provider_type="openai",
        name="oa",
        api_key="sk",
        base_url="https://api.openai.com/v1",
        model_id="gpt-4.1",
        is_enabled=True,
        sort_order=2,
    )
    cfg_claude = LLMProviderConfig(
        provider_type="claude",
        name="cl",
        api_key="ak",
        base_url="https://api.anthropic.com",
        model_id="claude-sonnet-4-6",
        is_enabled=True,
        sort_order=1,
    )
    db_session.add_all([cfg_openai, cfg_claude])
    await db_session.flush()
    db_session.add_all(
        [
            LLMStageAssignment(stage_key="outline", config_id=cfg_openai.id),
            LLMStageAssignment(stage_key="default", config_id=cfg_claude.id),
        ]
    )
    await db_session.flush()

    stage_map = await get_llm_providers_for_stages(db_session)

    # outline 首选 openai，claude 作为 default 兜底紧跟
    outline = stage_map["outline"]
    assert isinstance(outline[0], OpenAILLMProvider)
    assert any(isinstance(p, ClaudeLLMProvider) for p in outline)

    # default 首选 claude
    assert isinstance(stage_map["default"][0], ClaudeLLMProvider)

    # 未单独指派的 scene：default(claude) 优先
    assert isinstance(stage_map["scene"][0], ClaudeLLMProvider)


async def test_resolver_skips_disabled(db_session, monkeypatch) -> None:
    monkeypatch.setattr("app.providers.llm.get_effective_key", lambda k: None)
    cfg = LLMProviderConfig(
        provider_type="openai",
        name="oa",
        api_key="sk",
        base_url="https://api.openai.com/v1",
        model_id="gpt-4.1",
        is_enabled=False,
        sort_order=0,
    )
    db_session.add(cfg)
    await db_session.flush()
    stage_map = await get_llm_providers_for_stages(db_session)
    assert stage_map["default"] == []
