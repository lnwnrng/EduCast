"""CogVideoXProvider 测试 — httpx.MockTransport 拦截 submit/poll/download。"""

import json

import httpx

import app.providers.video_gen.base as vg_base
from app.config import settings
from app.providers.video_gen import get_video_gen_provider
from app.providers.video_gen.cogvideox import CogVideoXProvider


def _patch_transport(monkeypatch, handler) -> None:
    """把 base 模块内的 httpx.AsyncClient 替换为带 MockTransport 的版本。

    重构后 CogVideoXProvider 的 httpx 调用集中在 VideoGenProviderBase.
    _http_client（base.py），故 patch base 模块的 httpx。
    """
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def make_client(**kwargs):
        kwargs.pop("transport", None)
        kwargs.pop("proxy", None)
        return real_client(transport=transport, **kwargs)

    monkeypatch.setattr(vg_base.httpx, "AsyncClient", make_client)


async def test_generate_submit_poll_download(monkeypatch, tmp_path) -> None:
    """submit→轮询(PROCESSING→SUCCESS)→下载 mp4 落地。"""
    calls = {"poll": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/videos/generations"):
            assert request.headers.get("Authorization") == "Bearer k"
            body = json.loads(request.content)
            assert body["model"] == "cogvideox-flash"
            assert body["prompt"]
            assert "quality" not in body  # flash 档不带画质参数
            return httpx.Response(200, json={"id": "t1", "task_status": "PROCESSING"})
        if "/async-result/t1" in url:
            calls["poll"] += 1
            if calls["poll"] == 1:
                return httpx.Response(200, json={"task_status": "PROCESSING"})
            return httpx.Response(
                200,
                json={
                    "task_status": "SUCCESS",
                    "video_result": [{"url": "https://cdn.example/v.mp4"}],
                },
            )
        if url.endswith("/v.mp4"):
            return httpx.Response(200, content=b"VIDEODATA")
        return httpx.Response(404)

    _patch_transport(monkeypatch, handler)

    provider = CogVideoXProvider(api_key="k", model="cogvideox-flash", poll_interval=0)
    out = tmp_path / "gen.mp4"
    path = await provider.generate("数学课堂、简洁、粉笔风格 片头", str(out))

    assert path == str(out)
    assert out.read_bytes() == b"VIDEODATA"
    assert calls["poll"] == 2


async def test_poll_fail_status(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"task_status": "FAIL"})

    _patch_transport(monkeypatch, handler)
    provider = CogVideoXProvider(api_key="k", poll_interval=0)
    result = await provider.poll("t1")
    assert result.status == "failed"


async def test_submit_non_200_raises(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    _patch_transport(monkeypatch, handler)
    provider = CogVideoXProvider(api_key="k")
    import pytest

    with pytest.raises(RuntimeError):
        await provider.submit({"prompt": "x"})


def test_factory_none_without_any_key(monkeypatch, runtime_settings_dir) -> None:
    monkeypatch.setattr(settings, "COGVIDEO_API_KEY", "")
    monkeypatch.setattr(settings, "ZHIPU_API_KEY", "")
    assert get_video_gen_provider() is None


def test_factory_falls_back_to_zhipu_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "COGVIDEO_API_KEY", "")
    monkeypatch.setattr(settings, "ZHIPU_API_KEY", "z")
    provider = get_video_gen_provider()
    assert provider is not None
    assert provider.provider_name.startswith("cogvideox")


def test_flash_cost_is_zero() -> None:
    provider = CogVideoXProvider(api_key="k", model="cogvideox-flash")
    assert provider.estimate_cost({"duration_sec": 5}) == 0.0


def test_nonflash_cost_by_duration() -> None:
    provider = CogVideoXProvider(api_key="k", model="cogvideox-3")
    assert (
        provider.estimate_cost({"duration_sec": 5})
        == 5 * settings.VIDEO_GEN_COST_PER_SEC
    )
