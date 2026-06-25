"""视频生成模型管理 API + provider + 镜像测试。"""

from app.services.settings_service import load_runtime_settings

# ── 权限 ─────────────────────────────────────────────────


async def test_non_admin_forbidden(non_admin_auth_client) -> None:
    resp = await non_admin_auth_client.get("/api/v1/video-gen-providers/registry")
    assert resp.status_code == 403


async def test_admin_get_registry(auth_client) -> None:
    resp = await auth_client.get("/api/v1/video-gen-providers/registry")
    assert resp.status_code == 200
    types = {p["provider_type"] for p in resp.json()["providers"]}
    assert types == {"cogvideox", "kling", "minimax"}


# ── 配置 CRUD + 激活 + 镜像 ───────────────────────────────


async def test_create_activate_mirror(auth_client, runtime_settings_dir) -> None:
    # 新建（默认不激活）
    resp = await auth_client.post(
        "/api/v1/video-gen-providers/configs",
        json={
            "provider_type": "kling",
            "name": "我的可灵",
            "api_key": "sk-kling-1234567890",
            "base_url": "https://dashscope.aliyuncs.com",
            "model_id": "kling/kling-v3-video-generation",
            "is_enabled": True,
        },
    )
    assert resp.status_code == 201, resp.text
    cfg = resp.json()
    assert cfg["provider_type"] == "kling"
    assert "sk-kling-1234567890" not in cfg["api_key_masked"]
    cid = cfg["id"]
    # 未激活 → 运行时镜像为空
    rt = load_runtime_settings()
    assert not rt.get("VIDEO_GEN_API_KEY")

    # 激活 → 镜像写入
    resp = await auth_client.post(f"/api/v1/video-gen-providers/configs/{cid}/activate")
    assert resp.status_code == 200
    rt = load_runtime_settings()
    assert rt.get("VIDEO_GEN_PROVIDER_TYPE") == "kling"
    assert rt.get("VIDEO_GEN_API_KEY") == "sk-kling-1234567890"
    assert rt.get("VIDEO_GEN_MODEL") == "kling/kling-v3-video-generation"

    # 列表里 is_active=True
    resp = await auth_client.get("/api/v1/video-gen-providers/configs")
    items = {c["id"]: c for c in resp.json()}
    assert items[cid]["is_active"] is True

    # 删除 → 镜像清除
    await auth_client.delete(f"/api/v1/video-gen-providers/configs/{cid}")
    rt = load_runtime_settings()
    assert not rt.get("VIDEO_GEN_API_KEY")


async def test_activate_deactivates_others(auth_client, runtime_settings_dir) -> None:
    r1 = await auth_client.post(
        "/api/v1/video-gen-providers/configs",
        json={
            "provider_type": "cogvideox",
            "name": "a",
            "api_key": "k1-1234567890",
            "model_id": "cogvideox-flash",
        },
    )
    r2 = await auth_client.post(
        "/api/v1/video-gen-providers/configs",
        json={
            "provider_type": "minimax",
            "name": "b",
            "api_key": "k2-1234567890",
            "model_id": "MiniMax-Hailuo-2.3-Fast",
        },
    )
    id1, id2 = r1.json()["id"], r2.json()["id"]
    await auth_client.post(f"/api/v1/video-gen-providers/configs/{id1}/activate")
    assert load_runtime_settings().get("VIDEO_GEN_PROVIDER_TYPE") == "cogvideox"
    await auth_client.post(f"/api/v1/video-gen-providers/configs/{id2}/activate")
    rt = load_runtime_settings()
    assert rt.get("VIDEO_GEN_PROVIDER_TYPE") == "minimax"
    # id1 不再激活
    resp = await auth_client.get("/api/v1/video-gen-providers/configs")
    items = {c["id"]: c for c in resp.json()}
    assert items[id1]["is_active"] is False
    assert items[id2]["is_active"] is True


async def test_create_rejects_unknown_provider(auth_client) -> None:
    resp = await auth_client.post(
        "/api/v1/video-gen-providers/configs",
        json={"provider_type": "sora", "name": "x", "api_key": "k"},
    )
    assert resp.status_code == 400


# ── provider 构造 ───────────────────────────────────────


def test_build_provider_from_config_returns_right_class() -> None:
    from app.models.video_gen_provider import VideoGenProviderConfig
    from app.providers.video_gen import build_video_gen_provider_from_config
    from app.providers.video_gen.kling import KlingProvider
    from app.providers.video_gen.minimax import MiniMaxProvider

    cfg = VideoGenProviderConfig(
        provider_type="kling",
        name="cl",
        api_key="sk",
        base_url="https://dashscope.aliyuncs.com",
        model_id="kling/kling-v3-video-generation",
        is_enabled=True,
        is_active=False,
        sort_order=0,
    )
    assert isinstance(build_video_gen_provider_from_config(cfg), KlingProvider)
    cfg.provider_type = "minimax"
    cfg.model_id = "MiniMax-Hailuo-2.3-Fast"
    assert isinstance(build_video_gen_provider_from_config(cfg), MiniMaxProvider)
    cfg.provider_type = "unknown"
    assert build_video_gen_provider_from_config(cfg) is None


# ── get_video_gen_provider 同步回退 ───────────────────────


def test_factory_none_without_any_key(monkeypatch, runtime_settings_dir) -> None:
    from app.config import settings as s
    from app.providers.video_gen import get_video_gen_provider

    monkeypatch.setattr(s, "COGVIDEO_API_KEY", "")
    monkeypatch.setattr(s, "ZHIPU_API_KEY", "")
    assert get_video_gen_provider() is None


def test_factory_falls_back_to_zhipu(monkeypatch, runtime_settings_dir) -> None:
    from app.config import settings as s
    from app.providers.video_gen import get_video_gen_provider

    monkeypatch.setattr(s, "COGVIDEO_API_KEY", "")
    monkeypatch.setattr(s, "ZHIPU_API_KEY", "z")
    provider = get_video_gen_provider()
    assert provider is not None
    assert provider.provider_name.startswith("cogvideox")
