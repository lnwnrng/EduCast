"""settings_service 单元测试 — 运行时配置的加载、保存、有效值获取和定义结构校验。"""

import json

from app.config import settings
from app.services.settings_service import (
    API_KEY_DEFINITIONS,
    get_effective_key,
    get_effective_value,
    load_runtime_settings,
    save_runtime_settings,
)

# ── load_runtime_settings ──────────────────────────────────────────────


class TestLoadRuntimeSettings:
    """load_runtime_settings 读取 JSON 持久化文件。"""

    def test_returns_empty_when_file_missing(self, runtime_settings_dir):
        """文件不存在时返回空 dict。"""
        assert load_runtime_settings() == {}

    def test_returns_empty_on_corrupt_json(self, runtime_settings_dir):
        """JSON 损坏时返回空 dict（捕获异常）。"""
        (runtime_settings_dir / "_runtime_settings.json").write_text(
            "{invalid json", encoding="utf-8"
        )
        assert load_runtime_settings() == {}

    def test_returns_empty_on_non_dict_json(self, runtime_settings_dir):
        """合法 JSON 但非 dict 时返回空 dict。"""
        (runtime_settings_dir / "_runtime_settings.json").write_text(
            "[1, 2, 3]", encoding="utf-8"
        )
        assert load_runtime_settings() == {}

    def test_normal_file(self, runtime_settings_dir):
        """正常 JSON 文件返回正确数据。"""
        data = {"ZHIPU_API_KEY": "abc123", "EMAIL_FROM": "test@example.com"}
        (runtime_settings_dir / "_runtime_settings.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        result = load_runtime_settings()
        assert result == data


# ── save_runtime_settings ──────────────────────────────────────────────


class TestSaveRuntimeSettings:
    """save_runtime_settings 写入 JSON 文件。"""

    def test_save_creates_file(self, runtime_settings_dir):
        """保存后文件存在且内容正确。"""
        data = {"ZHIPU_API_KEY": "test_key"}
        save_runtime_settings(data)
        path = runtime_settings_dir / "_runtime_settings.json"
        assert path.exists()
        assert json.loads(path.read_text(encoding="utf-8")) == data

    def test_save_roundtrip(self, runtime_settings_dir):
        """save + load 往返一致。"""
        data = {"RESEND_API_KEY": "re_key_123", "EMAIL_FROM": "a@b.com"}
        save_runtime_settings(data)
        assert load_runtime_settings() == data

    def test_save_preserves_unicode(self, runtime_settings_dir):
        """ensure_ascii=False，中文原样存储。"""
        data = {"EMAIL_FROM": "测试 <a@b.com>"}
        save_runtime_settings(data)
        raw = (runtime_settings_dir / "_runtime_settings.json").read_text(
            encoding="utf-8"
        )
        assert "测试" in raw
        assert load_runtime_settings() == data


# ── get_effective_key ──────────────────────────────────────────────────


class TestGetEffectiveKey:
    """get_effective_key 优先运行时设置，其次环境变量。"""

    def test_runtime_takes_priority(self, runtime_settings_dir, monkeypatch):
        """运行时值优先于环境变量。"""
        save_runtime_settings({"ZHIPU_API_KEY": "runtime_key"})
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "env_key")
        assert get_effective_key("ZHIPU_API_KEY") == "runtime_key"

    def test_env_fallback_when_runtime_empty(self, runtime_settings_dir, monkeypatch):
        """运行时为空字符串时回退环境变量。"""
        save_runtime_settings({"ZHIPU_API_KEY": ""})
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "env_key")
        assert get_effective_key("ZHIPU_API_KEY") == "env_key"

    def test_env_fallback_when_runtime_missing(self, runtime_settings_dir, monkeypatch):
        """运行时文件中不含该 key 时回退环境变量。"""
        save_runtime_settings({})
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "env_key")
        assert get_effective_key("ZHIPU_API_KEY") == "env_key"

    def test_returns_none_when_both_empty(self, runtime_settings_dir, monkeypatch):
        """两层皆为空时返回 None。"""
        save_runtime_settings({})
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "")
        assert get_effective_key("ZHIPU_API_KEY") is None

    def test_whitespace_only_runtime_treated_as_empty(
        self, runtime_settings_dir, monkeypatch
    ):
        """纯空格运行时值视为空，回退环境变量。"""
        save_runtime_settings({"ZHIPU_API_KEY": "   "})
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "env_key")
        assert get_effective_key("ZHIPU_API_KEY") == "env_key"


# ── get_effective_value ────────────────────────────────────────────────


class TestGetEffectiveValue:
    """get_effective_value 优先运行时 → 环境变量 → 默认值。"""

    def test_runtime_takes_priority(self, runtime_settings_dir, monkeypatch):
        """运行时值优先。"""
        save_runtime_settings({"EMAIL_FROM": "runtime@test.com"})
        monkeypatch.setattr(settings, "EMAIL_FROM", "env@test.com")
        assert get_effective_value("EMAIL_FROM") == "runtime@test.com"

    def test_default_when_both_empty(self, runtime_settings_dir, monkeypatch):
        """两层皆空时使用默认值。"""
        save_runtime_settings({})
        monkeypatch.setattr(settings, "EMAIL_FROM", "")
        result = get_effective_value("EMAIL_FROM", "fallback@test.com")
        assert result == "fallback@test.com"

    def test_env_fallback_with_default(self, runtime_settings_dir, monkeypatch):
        """环境变量有值时优先于默认值。"""
        save_runtime_settings({})
        monkeypatch.setattr(settings, "EMAIL_FROM", "env@test.com")
        assert get_effective_value("EMAIL_FROM", "dflt") == "env@test.com"


# ── API_KEY_DEFINITIONS 结构校验 ───────────────────────────────────────


class TestApiKeyDefinitions:
    """API_KEY_DEFINITIONS 静态结构完整性。"""

    def test_has_five_items(self):
        # ZHIPU_API_KEY 已迁移至「LLM 管理」页面，系统设置剩 4 项
        assert len(API_KEY_DEFINITIONS) == 4

    def test_each_has_required_fields(self):
        required = {"key", "label", "description", "url", "features", "is_secret"}
        for defn in API_KEY_DEFINITIONS:
            missing = required - set(defn.keys())
            assert not missing, f"Missing fields in {defn.get('key')}: {missing}"

    def test_all_keys_unique(self):
        keys = [d["key"] for d in API_KEY_DEFINITIONS]
        assert len(set(keys)) == len(keys)

    def test_features_are_string_lists(self):
        for defn in API_KEY_DEFINITIONS:
            assert isinstance(defn["features"], list)
            assert all(isinstance(f, str) for f in defn["features"])

    def test_is_secret_is_boolean(self):
        for defn in API_KEY_DEFINITIONS:
            assert isinstance(defn["is_secret"], bool)

    def test_expected_keys_present(self):
        keys = {d["key"] for d in API_KEY_DEFINITIONS}
        expected = {
            "COGVIDEO_API_KEY",
            "RESEND_API_KEY",
            "EMAIL_FROM",
            "DIGITAL_HUMAN_API_KEY",
        }
        assert keys == expected

    def test_only_email_from_is_non_secret(self):
        non_secret = [d["key"] for d in API_KEY_DEFINITIONS if not d["is_secret"]]
        assert non_secret == ["EMAIL_FROM"]
