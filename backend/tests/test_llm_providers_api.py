"""LLM 模型管理 API 端点测试。"""

import pytest

from app.providers.base import ProviderResult
from app.services.settings_service import load_runtime_settings

pytestmark = pytest.mark.asyncio


# ── 权限 ───────────────────────────────────────────────


async def test_non_admin_get_registry_forbidden(non_admin_auth_client) -> None:
    resp = await non_admin_auth_client.get("/api/v1/llm-providers/registry")
    assert resp.status_code == 403


async def test_non_admin_list_configs_forbidden(non_admin_auth_client) -> None:
    resp = await non_admin_auth_client.get("/api/v1/llm-providers/configs")
    assert resp.status_code == 403


async def test_admin_can_get_registry(auth_client) -> None:
    resp = await auth_client.get("/api/v1/llm-providers/registry")
    assert resp.status_code == 200
    data = resp.json()
    provider_types = {p["provider_type"] for p in data["providers"]}
    assert provider_types == {"glm", "openai", "deepseek", "claude"}
    stage_keys = {s["stage_key"] for s in data["stages"]}
    assert "outline" in stage_keys and "default" in stage_keys


# ── 配置 CRUD ─────────────────────────────────────────


async def test_config_crud_flow(auth_client) -> None:
    # 新增
    resp = await auth_client.post(
        "/api/v1/llm-providers/configs",
        json={
            "provider_type": "openai",
            "name": "我的 OpenAI",
            "api_key": "sk-test-1234567890",
            "base_url": "https://api.openai.com/v1",
            "model_id": "gpt-4.1-mini",
            "is_enabled": True,
            "sort_order": 0,
            "thinking_disabled": True,
        },
    )
    assert resp.status_code == 201, resp.text
    cfg = resp.json()
    assert cfg["provider_type"] == "openai"
    assert cfg["model_id"] == "gpt-4.1-mini"
    # api_key 脱敏，不含原文
    assert "sk-test-1234567890" not in cfg["api_key_masked"]
    assert cfg["is_configured"] is True
    cid = cfg["id"]

    # 列表
    resp = await auth_client.get("/api/v1/llm-providers/configs")
    assert resp.status_code == 200
    items = resp.json()
    assert any(c["id"] == cid for c in items)

    # 更新（api_key 留空表示不变）
    resp = await auth_client.put(
        f"/api/v1/llm-providers/configs/{cid}",
        json={
            "name": "改名",
            "model_id": "gpt-4.1",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "改名"
    assert resp.json()["model_id"] == "gpt-4.1"

    # 删除
    resp = await auth_client.delete(f"/api/v1/llm-providers/configs/{cid}")
    assert resp.status_code == 200
    # 再列表应不存在
    resp = await auth_client.get("/api/v1/llm-providers/configs")
    assert not any(c["id"] == cid for c in resp.json())


async def test_create_config_rejects_unknown_provider(auth_client) -> None:
    resp = await auth_client.post(
        "/api/v1/llm-providers/configs",
        json={
            "provider_type": "gemini",
            "name": "x",
            "api_key": "k",
            "base_url": "",
            "model_id": "",
        },
    )
    assert resp.status_code == 400


async def test_update_config_404(auth_client) -> None:
    resp = await auth_client.put(
        "/api/v1/llm-providers/configs/00000000-0000-0000-0000-000000000000",
        json={"name": "x"},
    )
    assert resp.status_code == 404


# ── 阶段指派 ─────────────────────────────────────────


async def test_stage_assignment_flow(auth_client) -> None:
    # 先建一个配置
    resp = await auth_client.post(
        "/api/v1/llm-providers/configs",
        json={
            "provider_type": "glm",
            "name": "glm",
            "api_key": "z-1234567890",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "model_id": "glm-4.7-flash",
            "is_enabled": True,
            "sort_order": 0,
        },
    )
    cid = resp.json()["id"]

    # 列出阶段：默认 5 个，全部 config_id 为 None
    resp = await auth_client.get("/api/v1/llm-providers/stages")
    assert resp.status_code == 200
    stages = resp.json()
    assert len(stages) == 5
    assert all(s["config_id"] is None for s in stages)

    # 指派 outline → 该配置
    resp = await auth_client.put(
        "/api/v1/llm-providers/stages",
        json={
            "assignments": [
                {"stage_key": "outline", "config_id": cid},
                {"stage_key": "scene", "config_id": cid},
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    updated = {s["stage_key"]: s for s in resp.json()}
    assert updated["outline"]["config_id"] == cid
    assert updated["outline"]["config"]["provider_type"] == "glm"
    assert updated["scene"]["config_id"] == cid
    assert updated["default"]["config_id"] is None

    # 设回 None（跟随默认）
    resp = await auth_client.put(
        "/api/v1/llm-providers/stages",
        json={"assignments": [{"stage_key": "outline", "config_id": None}]},
    )
    updated = {s["stage_key"]: s for s in resp.json()}
    assert updated["outline"]["config_id"] is None


async def test_stage_assignment_rejects_unknown_stage(auth_client) -> None:
    resp = await auth_client.put(
        "/api/v1/llm-providers/stages",
        json={"assignments": [{"stage_key": "bogus", "config_id": None}]},
    )
    assert resp.status_code == 400


# ── 连通性测试 ───────────────────────────────────────


async def test_glm_config_mirrors_to_runtime_zhipu(
    auth_client, runtime_settings_dir
) -> None:
    """保存 GLM 配置后镜像到运行时 ZHIPU_API_KEY（供 CogVideoX/成本护栏复用）。

    这是「以 LLM 管理界面为主」的统一机制：系统设置不再管理 ZHIPU_API_KEY，
    LLM 管理保存的 GLM Key 自动同步到运行时，使视频生成等旧路径无需重复配置。
    """
    resp = await auth_client.post(
        "/api/v1/llm-providers/configs",
        json={
            "provider_type": "glm",
            "name": "glm",
            "api_key": "zhipu_mirror_key_12345",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "model_id": "glm-4.7-flash",
            "is_enabled": True,
        },
    )
    cid = resp.json()["id"]
    runtime = load_runtime_settings()
    assert runtime.get("ZHIPU_API_KEY") == "zhipu_mirror_key_12345"

    # 禁用该配置 → 镜像应清除
    await auth_client.put(
        f"/api/v1/llm-providers/configs/{cid}",
        json={"is_enabled": False},
    )
    runtime = load_runtime_settings()
    assert not runtime.get("ZHIPU_API_KEY")

    # 重新启用 → 镜像恢复
    await auth_client.put(
        f"/api/v1/llm-providers/configs/{cid}",
        json={"is_enabled": True},
    )
    assert load_runtime_settings().get("ZHIPU_API_KEY") == "zhipu_mirror_key_12345"

    # 删除 → 镜像清除
    await auth_client.delete(f"/api/v1/llm-providers/configs/{cid}")
    assert not load_runtime_settings().get("ZHIPU_API_KEY")


async def test_config_test_uses_provider_chat(auth_client, monkeypatch) -> None:
    """test 端点构造 provider 并调用 chat；用 fake provider 替换。"""

    class _FakeProvider:
        provider_name = "openai"

        async def chat(self, messages, **kwargs):  # noqa: ANN001
            return ProviderResult(task_id="t", status="completed", content="hi")

    monkeypatch.setattr(
        "app.api.v1.llm_providers.build_provider_from_config",
        lambda cfg: _FakeProvider(),
    )

    resp = await auth_client.post(
        "/api/v1/llm-providers/configs",
        json={
            "provider_type": "openai",
            "name": "oa",
            "api_key": "sk-test-1234567890",
            "base_url": "https://api.openai.com/v1",
            "model_id": "gpt-4.1-mini",
        },
    )
    cid = resp.json()["id"]

    resp = await auth_client.post(f"/api/v1/llm-providers/configs/{cid}/test")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "openai" in body["message"]


async def test_config_test_reports_failure(auth_client, monkeypatch) -> None:
    class _BoomProvider:
        provider_name = "openai"

        async def chat(self, messages, **kwargs):  # noqa: ANN001
            raise RuntimeError("HTTP 401: invalid")

    monkeypatch.setattr(
        "app.api.v1.llm_providers.build_provider_from_config",
        lambda cfg: _BoomProvider(),
    )

    resp = await auth_client.post(
        "/api/v1/llm-providers/configs",
        json={
            "provider_type": "openai",
            "name": "oa",
            "api_key": "sk-test-1234567890",
            "base_url": "https://api.openai.com/v1",
            "model_id": "gpt-4.1-mini",
        },
    )
    cid = resp.json()["id"]

    resp = await auth_client.post(f"/api/v1/llm-providers/configs/{cid}/test")
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
