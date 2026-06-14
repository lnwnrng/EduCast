"""verify_api_key 连通性验证测试 — 模拟外部 API 响应，验证各 Key 的检测逻辑。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.settings_service import (
    _verify_bigmodel_key,
    _verify_cogvideo_key,
    _verify_digital_human_key,
    _verify_email_from,
    _verify_resend_key,
    verify_api_key,
)

# ── 同步格式检查 ──────────────────────────────────────────────────────


class TestVerifyEmailFrom:
    """EMAIL_FROM 格式校验。"""

    def test_valid_full_format(self):
        """带名称的完整格式。"""
        result = _verify_email_from("EduCast <noreply@example.com>")
        assert result["ok"] is True

    def test_valid_bare_email(self):
        """纯邮箱地址。"""
        result = _verify_email_from("test@example.com")
        assert result["ok"] is True

    def test_invalid_no_at(self):
        """无 @ 符号。"""
        result = _verify_email_from("not-an-email")
        assert result["ok"] is False

    def test_invalid_no_domain(self):
        """@ 后无域名。"""
        result = _verify_email_from("user@")
        assert result["ok"] is False


class TestVerifyDigitalHumanKey:
    """DIGITAL_HUMAN_API_KEY 格式校验。"""

    def test_valid_key(self):
        result = _verify_digital_human_key("sk-abcdef12345")
        assert result["ok"] is True

    def test_too_short(self):
        result = _verify_digital_human_key("abc")
        assert result["ok"] is False


# ── 异步 API 探测（mock httpx）──────────────────────────────────────


def _mock_response(status_code: int, text: str = "") -> MagicMock:
    """构造 mock httpx.Response。"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


class TestVerifyBigmodelKey:
    """智谱 BigModel Key 探测（GLM / CogVideoX 共用）。"""

    @pytest.mark.asyncio
    async def test_success(self):
        """HTTP 200 → Key 有效。"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(200))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _verify_bigmodel_key("valid_key")
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_auth_failure(self):
        """HTTP 401 → 认证失败。"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(401))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _verify_bigmodel_key("bad_key")
        assert result["ok"] is False
        assert "认证失败" in result["message"]

    @pytest.mark.asyncio
    async def test_permission_denied(self):
        """HTTP 403 → 权限不足。"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(403))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _verify_bigmodel_key("no_perm_key")
        assert result["ok"] is False
        assert "权限不足" in result["message"]

    @pytest.mark.asyncio
    async def test_server_error(self):
        """HTTP 500 → 服务器错误。"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            return_value=_mock_response(500, "Internal Server Error")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _verify_bigmodel_key("key")
        assert result["ok"] is False
        assert "500" in result["message"]

    @pytest.mark.asyncio
    async def test_rate_limit_means_key_valid(self):
        """HTTP 429 → Key 有效但被限流。"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(429))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _verify_bigmodel_key("valid_key")
        assert result["ok"] is True
        assert "频率" in result["message"] or "限" in result["message"]


class TestVerifyResendKey:
    """Resend Key 探测。"""

    @pytest.mark.asyncio
    async def test_success(self):
        """HTTP 200 → Key 有效。"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(200))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _verify_resend_key("re_valid_key")
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_auth_failure(self):
        """HTTP 401/403 → 认证失败。"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(401))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _verify_resend_key("re_bad_key")
        assert result["ok"] is False
        assert "认证失败" in result["message"]

    @pytest.mark.asyncio
    async def test_restricted_key_is_valid(self):
        """受限 Key（restricted_api_key）返回 401 但 Key 实际有效。"""
        resp = _mock_response(
            401,
            '{"statusCode":401,"message":"restricted","name":"restricted_api_key"}',
        )
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _verify_resend_key("re_restricted_key")
        assert result["ok"] is True
        assert "受限" in result["message"] or "有效" in result["message"]


# ── verify_api_key 路由分发 ──────────────────────────────────────────


class TestVerifyCogvideoKey:
    """CogVideoX Key 探测（独立验证视频生成权限）。"""

    @pytest.mark.asyncio
    async def test_success_200(self):
        """HTTP 200 → Key 有效。"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(200))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _verify_cogvideo_key("valid_key")
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_auth_failure_401(self):
        """HTTP 401 → 认证失败。"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(401))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _verify_cogvideo_key("bad_key")
        assert result["ok"] is False
        assert "认证失败" in result["message"]

    @pytest.mark.asyncio
    async def test_permission_denied_403(self):
        """HTTP 403 → 未开通 CogVideoX 权限。"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(403))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _verify_cogvideo_key("no_perm")
        assert result["ok"] is False
        assert "权限不足" in result["message"]

    @pytest.mark.asyncio
    async def test_bad_request_400_means_auth_ok(self):
        """HTTP 400 → 认证通过，参数无效（Key 有效）。"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(400))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _verify_cogvideo_key("valid_key")
        assert result["ok"] is True
        assert "认证通过" in result["message"]

    @pytest.mark.asyncio
    async def test_rate_limit_429_means_key_valid(self):
        """HTTP 429 → Key 有效但被限流。"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(429))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _verify_cogvideo_key("valid_key")
        assert result["ok"] is True
        assert "访问量" in result["message"] or "限" in result["message"]


class TestVerifyApiKeyDispatch:
    """verify_api_key 按 key_name 分发到对应验证函数。"""

    @pytest.mark.asyncio
    async def test_empty_value(self):
        """空值直接返回失败。"""
        result = await verify_api_key("ZHIPU_API_KEY", "")
        assert result["ok"] is False
        assert "为空" in result["message"]

    @pytest.mark.asyncio
    async def test_whitespace_only(self):
        """纯空格视为空。"""
        result = await verify_api_key("ZHIPU_API_KEY", "   ")
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_unknown_key(self):
        """未知配置项返回失败。"""
        result = await verify_api_key("UNKNOWN_KEY", "some_value")
        assert result["ok"] is False
        assert "未知" in result["message"]

    @pytest.mark.asyncio
    async def test_dispatch_zhipu(self):
        """ZHIPU_API_KEY 分发到 BigModel 验证。"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(200))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await verify_api_key("ZHIPU_API_KEY", "test_key")
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_dispatch_cogvideo(self):
        """COGVIDEO_API_KEY 走 CogVideoX 独立验证。"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(200))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await verify_api_key("COGVIDEO_API_KEY", "test_key")
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_dispatch_resend(self):
        """RESEND_API_KEY 分发到 Resend 验证。"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(200))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await verify_api_key("RESEND_API_KEY", "re_key")
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_dispatch_email_from(self):
        """EMAIL_FROM 走格式校验。"""
        result = await verify_api_key("EMAIL_FROM", "test@example.com")
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_dispatch_digital_human(self):
        """DIGITAL_HUMAN_API_KEY 走格式校验。"""
        result = await verify_api_key("DIGITAL_HUMAN_API_KEY", "sk-12345678")
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_exception_caught(self):
        """验证过程中抛异常被捕获。"""
        with patch("httpx.AsyncClient", side_effect=Exception("network down")):
            result = await verify_api_key("ZHIPU_API_KEY", "key")
        assert result["ok"] is False
        assert "验证失败" in result["message"]
