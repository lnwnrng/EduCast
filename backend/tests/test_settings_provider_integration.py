"""Provider 集成验证 — 运行时 Key 配置对 Provider 工厂、成本计费和邮件的影响。"""

import pytest

from app.config import settings
from app.ir.schema import SceneType
from app.services.settings_service import save_runtime_settings

# ── LLM Provider ───────────────────────────────────────────────────────


class TestLLMProviderIntegration:
    """get_llm_provider() 读取运行时 ZHIPU_API_KEY。"""

    def test_provider_from_runtime_key(self, runtime_settings_dir, monkeypatch):
        """运行时配置 ZHIPU_API_KEY → 返回 Provider 实例。"""
        save_runtime_settings({"ZHIPU_API_KEY": "runtime_zhipu_key"})
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "")
        from app.providers.llm import get_llm_provider

        provider = get_llm_provider()
        assert provider is not None
        assert provider._api_key == "runtime_zhipu_key"

    def test_provider_from_env_key(self, runtime_settings_dir, monkeypatch):
        """环境变量 ZHIPU_API_KEY → 返回 Provider 实例。"""
        save_runtime_settings({})
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "env_zhipu_key")
        from app.providers.llm import get_llm_provider

        provider = get_llm_provider()
        assert provider is not None
        assert provider._api_key == "env_zhipu_key"

    def test_provider_none_when_no_key(self, runtime_settings_dir, monkeypatch):
        """两层皆无 key → 返回 None（降级）。"""
        save_runtime_settings({})
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "")
        from app.providers.llm import get_llm_provider

        assert get_llm_provider() is None


# ── Video Gen Provider 回退链 ──────────────────────────────────────────


class TestVideoGenProviderIntegration:
    """get_video_gen_provider() 的 COGVIDEO → ZHIPU 回退链。"""

    def test_prefers_cogvideo_key(self, runtime_settings_dir, monkeypatch):
        """COGVIDEO_API_KEY 优先于 ZHIPU_API_KEY。"""
        save_runtime_settings(
            {
                "COGVIDEO_API_KEY": "cog_key",
                "ZHIPU_API_KEY": "zhipu_key",
            }
        )
        monkeypatch.setattr(settings, "COGVIDEO_API_KEY", "")
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "")
        from app.providers.video_gen import get_video_gen_provider

        provider = get_video_gen_provider()
        assert provider is not None
        assert provider._api_key == "cog_key"

    def test_falls_back_to_zhipu(self, runtime_settings_dir, monkeypatch):
        """COGVIDEO 为空时回退 ZHIPU_API_KEY。"""
        save_runtime_settings({"ZHIPU_API_KEY": "zhipu_key"})
        monkeypatch.setattr(settings, "COGVIDEO_API_KEY", "")
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "")
        from app.providers.video_gen import get_video_gen_provider

        provider = get_video_gen_provider()
        assert provider is not None
        assert provider._api_key == "zhipu_key"

    def test_none_when_both_empty(self, runtime_settings_dir, monkeypatch):
        """两者皆空 → 返回 None。"""
        save_runtime_settings({})
        monkeypatch.setattr(settings, "COGVIDEO_API_KEY", "")
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "")
        from app.providers.video_gen import get_video_gen_provider

        assert get_video_gen_provider() is None

    def test_runtime_cogvideo_overrides_env_zhipu(
        self, runtime_settings_dir, monkeypatch
    ):
        """运行时 COGVIDEO 优先于环境变量 ZHIPU。"""
        save_runtime_settings({"COGVIDEO_API_KEY": "rt_cog"})
        monkeypatch.setattr(settings, "COGVIDEO_API_KEY", "")
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "env_zhipu")
        from app.providers.video_gen import get_video_gen_provider

        provider = get_video_gen_provider()
        assert provider is not None
        assert provider._api_key == "rt_cog"


# ── Cost Service 动态计费 ──────────────────────────────────────────────


class TestCostServiceIntegration:
    """cost_service._is_billed() 按运行时 Key 配置动态判断计费。"""

    def test_digital_human_billed_with_key(self, runtime_settings_dir, monkeypatch):
        """数字人有 key → billed=True。"""
        save_runtime_settings({"DIGITAL_HUMAN_API_KEY": "dh_key"})
        monkeypatch.setattr(settings, "DIGITAL_HUMAN_API_KEY", "")
        from app.services.cost_service import _is_billed

        assert _is_billed(SceneType.DIGITAL_HUMAN) is True

    def test_digital_human_not_billed_without_key(
        self, runtime_settings_dir, monkeypatch
    ):
        """数字人无 key → billed=False。"""
        save_runtime_settings({})
        monkeypatch.setattr(settings, "DIGITAL_HUMAN_API_KEY", "")
        from app.services.cost_service import _is_billed

        assert _is_billed(SceneType.DIGITAL_HUMAN) is False

    def test_generative_clip_billed_with_zhipu_only(
        self, runtime_settings_dir, monkeypatch
    ):
        """仅配 ZHIPU → generative_clip billed=True（回退）。"""
        save_runtime_settings({"ZHIPU_API_KEY": "zhipu_key"})
        monkeypatch.setattr(settings, "COGVIDEO_API_KEY", "")
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "")
        from app.services.cost_service import _is_billed

        assert _is_billed(SceneType.GENERATIVE_CLIP) is True

    def test_slide_always_free(self, runtime_settings_dir, monkeypatch):
        """SLIDE 永远免费。"""
        save_runtime_settings({"ZHIPU_API_KEY": "key"})
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "key")
        from app.services.cost_service import _is_billed

        assert _is_billed(SceneType.SLIDE) is False

    def test_generative_clip_not_billed_without_keys(
        self, runtime_settings_dir, monkeypatch
    ):
        """无 COGVIDEO 也无 ZHIPU → generative_clip billed=False。"""
        save_runtime_settings({})
        monkeypatch.setattr(settings, "COGVIDEO_API_KEY", "")
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "")
        from app.services.cost_service import _is_billed

        assert _is_billed(SceneType.GENERATIVE_CLIP) is False


# ── Email Service ──────────────────────────────────────────────────────


class TestEmailServiceIntegration:
    """email_service 使用运行时 RESEND_API_KEY 和 EMAIL_FROM。"""

    @pytest.mark.asyncio
    async def test_skips_without_resend_key(self, runtime_settings_dir, monkeypatch):
        """无 RESEND_API_KEY → 静默跳过（不抛异常）。"""
        save_runtime_settings({})
        monkeypatch.setattr(settings, "RESEND_API_KEY", "")
        from app.services.email_service import EmailService

        # 应该直接返回，不抛异常
        await EmailService.send_verification_code("test@example.com", "123456")

    @pytest.mark.asyncio
    async def test_uses_runtime_email_from(self, runtime_settings_dir, monkeypatch):
        """运行时 EMAIL_FROM 生效。"""
        save_runtime_settings(
            {
                "RESEND_API_KEY": "fake_resend_key",
                "EMAIL_FROM": "custom@test.com",
            }
        )
        monkeypatch.setattr(settings, "RESEND_API_KEY", "")
        monkeypatch.setattr(settings, "EMAIL_FROM", "default@test.com")

        from unittest.mock import AsyncMock, MagicMock

        from app.services.email_service import EmailService

        captured = {}

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        # 拦截 post 调用并捕获 payload
        async def capturing_post(*args, **kwargs):
            captured["payload"] = kwargs.get("json", {})
            return mock_resp

        mock_client.post = capturing_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        import httpx

        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        await EmailService.send_verification_code("user@test.com", "654321")
        assert captured.get("payload", {}).get("from") == "custom@test.com"

    @pytest.mark.asyncio
    async def test_falls_back_to_settings_email_from(
        self, runtime_settings_dir, monkeypatch
    ):
        """运行时 EMAIL_FROM 为空时回退 settings.EMAIL_FROM。"""
        save_runtime_settings({"RESEND_API_KEY": "fake_resend_key"})
        monkeypatch.setattr(settings, "RESEND_API_KEY", "")
        monkeypatch.setattr(settings, "EMAIL_FROM", "default@test.com")

        from unittest.mock import AsyncMock, MagicMock

        from app.services.email_service import EmailService

        captured = {}

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        async def capturing_post(*args, **kwargs):
            captured["payload"] = kwargs.get("json", {})
            return mock_resp

        mock_client.post = capturing_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        import httpx

        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        await EmailService.send_verification_code("user@test.com", "654321")
        assert captured.get("payload", {}).get("from") == "default@test.com"
