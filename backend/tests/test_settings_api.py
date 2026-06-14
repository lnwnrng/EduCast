"""settings API 集成测试 — 端点权限、脱敏逻辑、白名单过滤和端到端一致性。"""


import pytest

from app.services.settings_service import save_runtime_settings

# ── GET /api/v1/settings/api-keys ──────────────────────────────────────


class TestGetApiKeys:
    """GET /api/v1/settings/api-keys — 获取 API Key 定义和状态。"""

    @pytest.mark.asyncio
    async def test_admin_gets_all_definitions(self, auth_client, runtime_settings_dir):
        """admin 获取全部 5 项定义。"""
        resp = await auth_client.get("/api/v1/settings/api-keys")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 5
        for item in data["items"]:
            assert "key" in item
            assert "label" in item
            assert "is_configured" in item
            assert "masked_value" in item
            assert "is_secret" in item

    @pytest.mark.asyncio
    async def test_non_admin_gets_empty(
        self, non_admin_auth_client, runtime_settings_dir,
    ):
        """非 admin 返回空 items。"""
        resp = await non_admin_auth_client.get("/api/v1/settings/api-keys")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert "仅管理员" in data.get("message", "")

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client, runtime_settings_dir):
        """未认证返回 401。"""
        resp = await client.get("/api/v1/settings/api-keys")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_masking_long_secret(self, auth_client, runtime_settings_dir):
        """密钥 >10 字符：前6+****+后4。"""
        save_runtime_settings({"ZHIPU_API_KEY": "abcdefghijklmnop1234"})  # 20 chars
        resp = await auth_client.get("/api/v1/settings/api-keys")
        items = {i["key"]: i for i in resp.json()["items"]}
        assert items["ZHIPU_API_KEY"]["masked_value"] == "abcdef****1234"
        assert items["ZHIPU_API_KEY"]["is_configured"] is True

    @pytest.mark.asyncio
    async def test_masking_short_secret(self, auth_client, runtime_settings_dir):
        """密钥 ≤10 字符：****。"""
        save_runtime_settings({"RESEND_API_KEY": "12345678"})  # 8 chars
        resp = await auth_client.get("/api/v1/settings/api-keys")
        items = {i["key"]: i for i in resp.json()["items"]}
        assert items["RESEND_API_KEY"]["masked_value"] == "****"

    @pytest.mark.asyncio
    async def test_non_secret_shows_full_value(self, auth_client, runtime_settings_dir):
        """非密钥项显示完整值。"""
        save_runtime_settings({"EMAIL_FROM": "my@email.com"})
        resp = await auth_client.get("/api/v1/settings/api-keys")
        items = {i["key"]: i for i in resp.json()["items"]}
        assert items["EMAIL_FROM"]["masked_value"] == "my@email.com"

    @pytest.mark.asyncio
    async def test_is_configured_reflects_runtime(
        self, auth_client, runtime_settings_dir,
    ):
        """is_configured 正确反映运行时配置状态。"""
        save_runtime_settings({"ZHIPU_API_KEY": "some_key"})
        resp = await auth_client.get("/api/v1/settings/api-keys")
        items = {i["key"]: i for i in resp.json()["items"]}
        assert items["ZHIPU_API_KEY"]["is_configured"] is True
        assert items["RESEND_API_KEY"]["is_configured"] is False
        assert items["EMAIL_FROM"]["is_configured"] is False

    @pytest.mark.asyncio
    async def test_masking_boundary_10_chars(self, auth_client, runtime_settings_dir):
        """密钥恰好 10 字符 → ****。"""
        save_runtime_settings({"RESEND_API_KEY": "1234567890"})  # 10 chars
        resp = await auth_client.get("/api/v1/settings/api-keys")
        items = {i["key"]: i for i in resp.json()["items"]}
        assert items["RESEND_API_KEY"]["masked_value"] == "****"

    @pytest.mark.asyncio
    async def test_masking_boundary_11_chars(self, auth_client, runtime_settings_dir):
        """密钥恰好 11 字符 → 前6+****+后4。"""
        save_runtime_settings({"RESEND_API_KEY": "12345678901"})  # 11 chars
        resp = await auth_client.get("/api/v1/settings/api-keys")
        items = {i["key"]: i for i in resp.json()["items"]}
        assert items["RESEND_API_KEY"]["masked_value"] == "123456****8901"


# ── GET /api/v1/settings/api-keys/values ───────────────────────────────


class TestGetApiKeyValues:
    """GET /api/v1/settings/api-keys/values — 获取原始值用于编辑回填。"""

    @pytest.mark.asyncio
    async def test_admin_gets_raw_values(self, auth_client, runtime_settings_dir):
        """admin 获取未脱敏的原始值。"""
        save_runtime_settings({"ZHIPU_API_KEY": "my_secret_key_123"})
        resp = await auth_client.get("/api/v1/settings/api-keys/values")
        assert resp.status_code == 200
        data = resp.json()
        assert data["settings"]["ZHIPU_API_KEY"] == "my_secret_key_123"

    @pytest.mark.asyncio
    async def test_empty_for_unset_keys(self, auth_client, runtime_settings_dir):
        """未配置的 key 值为空字符串。"""
        resp = await auth_client.get("/api/v1/settings/api-keys/values")
        data = resp.json()
        for key in ["ZHIPU_API_KEY", "COGVIDEO_API_KEY", "RESEND_API_KEY",
                     "EMAIL_FROM", "DIGITAL_HUMAN_API_KEY"]:
            assert data["settings"][key] == ""

    @pytest.mark.asyncio
    async def test_non_admin_gets_empty(
        self, non_admin_auth_client, runtime_settings_dir,
    ):
        """非 admin 返回空 settings。"""
        resp = await non_admin_auth_client.get("/api/v1/settings/api-keys/values")
        assert resp.status_code == 200
        assert resp.json()["settings"] == {}

    @pytest.mark.asyncio
    async def test_extra_keys_not_returned(self, auth_client, runtime_settings_dir):
        """运行时文件中额外的非法 key 不出现在返回值中。"""
        save_runtime_settings({
            "ZHIPU_API_KEY": "good",
            "HACK_KEY": "evil",
        })
        resp = await auth_client.get("/api/v1/settings/api-keys/values")
        data = resp.json()
        assert "HACK_KEY" not in data["settings"]
        assert data["settings"]["ZHIPU_API_KEY"] == "good"


# ── PUT /api/v1/settings/api-keys ──────────────────────────────────────


class TestUpdateApiKeys:
    """PUT /api/v1/settings/api-keys — 保存配置。"""

    @pytest.mark.asyncio
    async def test_admin_save_success(self, auth_client, runtime_settings_dir):
        """admin 正常保存。"""
        resp = await auth_client.put("/api/v1/settings/api-keys", json={
            "settings": {"ZHIPU_API_KEY": "new_key_123"}
        })
        assert resp.status_code == 200
        assert "已保存" in resp.json()["message"]

    @pytest.mark.asyncio
    async def test_whitelist_filters_illegal_keys(
        self, auth_client, runtime_settings_dir,
    ):
        """白名单过滤非法 key，合法 key 正常写入。"""
        await auth_client.put("/api/v1/settings/api-keys", json={
            "settings": {"HACK_KEY": "evil", "ZHIPU_API_KEY": "good"}
        })
        # 读取文件验证
        from app.services.settings_service import load_runtime_settings
        data = load_runtime_settings()
        assert "HACK_KEY" not in data
        assert data["ZHIPU_API_KEY"] == "good"

    @pytest.mark.asyncio
    async def test_non_admin_rejected(
        self, non_admin_auth_client, runtime_settings_dir,
    ):
        """非 admin 拒绝修改。"""
        resp = await non_admin_auth_client.put("/api/v1/settings/api-keys", json={
            "settings": {"ZHIPU_API_KEY": "should_not_save"}
        })
        assert resp.status_code == 200
        assert "仅管理员" in resp.json()["message"]
        # 验证未写入
        from app.services.settings_service import load_runtime_settings
        data = load_runtime_settings()
        assert data.get("ZHIPU_API_KEY", "") == ""

    @pytest.mark.asyncio
    async def test_unauthenticated_rejected(self, client, runtime_settings_dir):
        """未认证返回 401。"""
        resp = await client.put("/api/v1/settings/api-keys", json={
            "settings": {"ZHIPU_API_KEY": "nope"}
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_save_strips_whitespace(self, auth_client, runtime_settings_dir):
        """值自动 strip 前后空格。"""
        await auth_client.put("/api/v1/settings/api-keys", json={
            "settings": {"ZHIPU_API_KEY": "  key_with_spaces  "}
        })
        from app.services.settings_service import load_runtime_settings
        data = load_runtime_settings()
        assert data["ZHIPU_API_KEY"] == "key_with_spaces"

    @pytest.mark.asyncio
    async def test_save_preserves_existing_keys(
        self, auth_client, runtime_settings_dir,
    ):
        """保存不覆盖已有的其他 key（merge 语义）。"""
        save_runtime_settings({"RESEND_API_KEY": "existing_key"})
        await auth_client.put("/api/v1/settings/api-keys", json={
            "settings": {"ZHIPU_API_KEY": "new_key"}
        })
        from app.services.settings_service import load_runtime_settings
        data = load_runtime_settings()
        assert data["RESEND_API_KEY"] == "existing_key"
        assert data["ZHIPU_API_KEY"] == "new_key"

    @pytest.mark.asyncio
    async def test_save_message_lists_configured(
        self, auth_client, runtime_settings_dir,
    ):
        """返回消息列出已配置 key。"""
        resp = await auth_client.put("/api/v1/settings/api-keys", json={
            "settings": {
                "ZHIPU_API_KEY": "key1",
                "RESEND_API_KEY": "key2",
            }
        })
        msg = resp.json()["message"]
        assert "ZHIPU_API_KEY" in msg
        assert "RESEND_API_KEY" in msg


# ── 端到端一致性 ───────────────────────────────────────────────────────


class TestEndToEnd:
    """PUT → GET 端到端一致性验证。"""

    @pytest.mark.asyncio
    async def test_put_then_get_consistency(self, auth_client, runtime_settings_dir):
        """PUT 写入 → GET api-keys 验证状态 → GET values 验证原值。"""
        await auth_client.put("/api/v1/settings/api-keys", json={
            "settings": {
                "ZHIPU_API_KEY": "zhipu_secret_12345",
                "EMAIL_FROM": "test@example.com",
                "RESEND_API_KEY": "re_key",
            }
        })

        # GET api-keys 验证状态和脱敏
        resp = await auth_client.get("/api/v1/settings/api-keys")
        items = {i["key"]: i for i in resp.json()["items"]}
        assert items["ZHIPU_API_KEY"]["is_configured"] is True
        assert items["ZHIPU_API_KEY"]["masked_value"] == "zhipu_****2345"  # >10 chars
        assert items["EMAIL_FROM"]["masked_value"] == "test@example.com"  # non-secret
        assert items["RESEND_API_KEY"]["masked_value"] == "****"  # <=10 chars

        # GET values 验证原始值
        resp = await auth_client.get("/api/v1/settings/api-keys/values")
        vals = resp.json()["settings"]
        assert vals["ZHIPU_API_KEY"] == "zhipu_secret_12345"
        assert vals["EMAIL_FROM"] == "test@example.com"
        assert vals["RESEND_API_KEY"] == "re_key"

    @pytest.mark.asyncio
    async def test_overwrite_then_read(self, auth_client, runtime_settings_dir):
        """覆盖写入生效。"""
        await auth_client.put("/api/v1/settings/api-keys", json={
            "settings": {"ZHIPU_API_KEY": "v1"}
        })
        await auth_client.put("/api/v1/settings/api-keys", json={
            "settings": {"ZHIPU_API_KEY": "v2"}
        })
        resp = await auth_client.get("/api/v1/settings/api-keys/values")
        assert resp.json()["settings"]["ZHIPU_API_KEY"] == "v2"

    @pytest.mark.asyncio
    async def test_clear_key_by_sending_empty(self, auth_client, runtime_settings_dir):
        """发送空字符串清空 key。"""
        await auth_client.put("/api/v1/settings/api-keys", json={
            "settings": {"ZHIPU_API_KEY": "some_value"}
        })
        await auth_client.put("/api/v1/settings/api-keys", json={
            "settings": {"ZHIPU_API_KEY": ""}
        })
        resp = await auth_client.get("/api/v1/settings/api-keys")
        items = {i["key"]: i for i in resp.json()["items"]}
        assert items["ZHIPU_API_KEY"]["is_configured"] is False
