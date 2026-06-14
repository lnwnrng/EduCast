"""运行时设置服务 — 通过前端 UI 配置 API Key 等参数，持久化到 JSON 文件。"""

import json
import logging
import os

import httpx

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


# ── API Key 连通性验证 ──────────────────────────────────────────────


async def verify_api_key(key_name: str, key_value: str) -> dict:
    """验证指定 API Key 是否可用，返回 {ok, message}。

    对每个 Key 发起真实的最小化 API 探测：
    - ZHIPU / COGVIDEO: 发 max_tokens=1 的 chat/completions
    - RESEND: 调用 GET /api-keys 检查认证
    - DIGITAL_HUMAN / EMAIL_FROM: 无通用探测接口，仅检查格式
    """
    key_value = key_value.strip()
    if not key_value:
        return {"ok": False, "message": "Key 为空，请先填写后再检测"}

    try:
        if key_name in ("ZHIPU_API_KEY", "COGVIDEO_API_KEY"):
            return await _verify_bigmodel_key(key_value)
        elif key_name == "RESEND_API_KEY":
            return await _verify_resend_key(key_value)
        elif key_name == "DIGITAL_HUMAN_API_KEY":
            return _verify_digital_human_key(key_value)
        elif key_name == "EMAIL_FROM":
            return _verify_email_from(key_value)
        else:
            return {"ok": False, "message": f"未知的配置项: {key_name}"}
    except Exception as e:
        logger.warning("验证 %s 时异常: %s", key_name, e)
        return {"ok": False, "message": f"验证异常: {e}"}


async def _verify_bigmodel_key(api_key: str) -> dict:
    """智谱 BigModel 平台 Key 验证（GLM / CogVideoX 共用）。"""
    url = settings.ZHIPU_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.ZHIPU_MODEL,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
    if resp.status_code == 200:
        return {"ok": True, "message": "智谱 API 连通，Key 有效"}
    if resp.status_code == 401:
        return {"ok": False, "message": "认证失败：Key 无效或已过期"}
    if resp.status_code == 403:
        return {"ok": False, "message": "权限不足：请检查 Key 权限设置"}
    return {
        "ok": False,
        "message": f"API 返回 HTTP {resp.status_code}: {resp.text[:200]}",
    }


async def _verify_resend_key(api_key: str) -> dict:
    """Resend API Key 验证 — 调用 GET /api-keys 探测认证。"""
    url = "https://api.resend.com/api-keys"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code == 200:
        return {"ok": True, "message": "Resend API 连通，Key 有效"}
    if resp.status_code in (401, 403):
        return {"ok": False, "message": "认证失败：Key 无效或权限不足"}
    return {
        "ok": False,
        "message": f"Resend API 返回 HTTP {resp.status_code}",
    }


def _verify_digital_human_key(api_key: str) -> dict:
    """数字人 Key 格式检查（无通用探测接口）。"""
    if len(api_key) < 8:
        return {"ok": False, "message": "Key 长度过短，请检查"}
    return {
        "ok": True,
        "message": "Key 格式正常（数字人 API 无通用探测，已保存后将在生成时自动生效）",
    }


def _verify_email_from(value: str) -> dict:
    """邮件发件人地址格式检查。"""
    if "<" in value and ">" in value and "@" in value:
        return {"ok": True, "message": "格式正确（如 EduCast <noreply@domain.com>）"}
    if "@" in value and "." in value.split("@")[-1]:
        return {"ok": True, "message": "格式正确"}
    return {"ok": False, "message": "格式不正确，请输入有效邮箱地址"}
