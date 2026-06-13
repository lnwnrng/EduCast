"""运行时设置服务 — 通过前端 UI 配置 API Key 等参数，持久化到 JSON 文件。"""

import json
import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)

_SETTINGS_FILE = "_runtime_settings.json"


def _settings_path() -> str:
    return os.path.join(settings.STORAGE_ROOT, _SETTINGS_FILE)


def load_runtime_settings() -> dict:
    """加载运行时设置（JSON 文件）。"""
    path = _settings_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        logger.warning("加载运行时设置失败，返回空配置")
        return {}


def save_runtime_settings(data: dict) -> None:
    """保存运行时设置到 JSON 文件。"""
    os.makedirs(settings.STORAGE_ROOT, exist_ok=True)
    path = _settings_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_effective_key(env_key: str) -> str | None:
    """获取有效的 API Key：优先运行时设置，其次环境变量。"""
    runtime = load_runtime_settings()
    val = runtime.get(env_key, "").strip()
    if val:
        return val
    env_val = getattr(settings, env_key, "")
    return env_val if env_val else None


def get_effective_value(env_key: str, default: str = "") -> str:
    """获取有效的配置值（非密钥类）：优先运行时设置，其次环境变量，最后默认值。"""
    runtime = load_runtime_settings()
    val = runtime.get(env_key, "").strip()
    if val:
        return val
    env_val = getattr(settings, env_key, "")
    return env_val if env_val else default


# ── 可配置的 API Key 定义（供前端展示）──

API_KEY_DEFINITIONS = [
    {
        "key": "ZHIPU_API_KEY",
        "label": "智谱 API Key",
        "description": "用于 LLM 脚本编排（GLM-4.7-Flash，免费）和 AI 视频生成（CogVideoX-Flash，免费）。在 open.bigmodel.cn 注册获取。",
        "url": "https://open.bigmodel.cn",
        "features": ["LLM 脚本编排", "AI 全生成模式（CogVideoX）"],
        "is_secret": True,
    },
    {
        "key": "COGVIDEO_API_KEY",
        "label": "CogVideoX 视频生成 Key",
        "description": "独立于智谱 GLM 的视频生成 Key。通常无需单独配置，留空时自动回退使用上方的智谱 API Key。仅当你需要为视频生成使用不同账号时才需填写。",
        "url": "https://open.bigmodel.cn",
        "features": ["AI 视频生成（CogVideoX）"],
        "is_secret": True,
    },
    {
        "key": "RESEND_API_KEY",
        "label": "Resend 邮件 API Key",
        "description": "用于注册时的邮箱验证码发送。在 resend.com 注册获取。",
        "url": "https://resend.com",
        "features": ["邮箱验证码"],
        "is_secret": True,
    },
    {
        "key": "EMAIL_FROM",
        "label": "邮件发件人地址",
        "description": "验证码邮件的发件人地址。必须是 Resend 验证过的域名，格式如：EduCast <noreply@yourdomain.com>",
        "url": "",
        "features": ["邮箱验证码"],
        "is_secret": False,
    },
    {
        "key": "DIGITAL_HUMAN_API_KEY",
        "label": "数字人 API Key",
        "description": "接入云端真人口播视频（如阿里百炼 wan2.2-s2v）。不配置则使用本地讲师画中画兜底。",
        "url": "",
        "features": ["数字人讲解"],
        "is_secret": True,
    },
]
