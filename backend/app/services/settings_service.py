"""运行时设置服务 — 通过前端 UI 配置 API Key 等参数，持久化到 JSON 文件。"""

import json
import logging
import os

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_SETTINGS_FILE = "_runtime_settings.json"


def _get_proxy_url() -> str | None:
    """返回配置的 HTTP 代理地址，空字符串返回 None。"""
    proxy = settings.HTTP_PROXY.strip()
    return proxy if proxy else None


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


def set_runtime_setting(key: str, value: str | None) -> None:
    """写入/清除单个运行时设置项（merge 语义，不影响其它 key）。

    value 为空字符串或 None 时删除该 key。供 LLM 管理 页保存 GLM Key 后
    同步镜像到 ZHIPU_API_KEY（供 CogVideoX / 成本护栏等仍读运行时 Key 的
    旧路径使用，使「LLM 管理」成为智谱 Key 的唯一配置入口）。
    """
    runtime = load_runtime_settings()
    if value is None or not value.strip():
        runtime.pop(key, None)
    else:
        runtime[key] = value.strip()
    save_runtime_settings(runtime)


# ── 可配置的 API Key 定义（供前端展示）──
# 注意：LLM（智谱 GLM）的 Key 已迁移至「LLM 管理」页面（DB 管理），
# 此处不再列出 ZHIPU_API_KEY。LLM 管理保存 GLM 配置时会镜像写入运行时
# ZHIPU_API_KEY，供 CogVideoX / 成本护栏复用。

API_KEY_DEFINITIONS = [
    {
        "key": "COGVIDEO_API_KEY",
        "label": "CogVideoX 视频生成 Key",
        "description": (
            "智谱 CogVideoX 视频生成 Key（与 GLM 同平台同 Key）。"
            "LLM 脚本编排的 GLM Key 请到「LLM 管理」页面配置。"
            "此处仅为视频生成使用不同账号而设；留空时自动复用"
            "「LLM 管理」中配置的 GLM Key（或回退 .env 的 ZHIPU_API_KEY）。"
        ),
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
        "description": (
            "验证码邮件的发件人地址。"
            "必须是 Resend 验证过的域名，"
            "格式如：EduCast <noreply@yourdomain.com>"
        ),
        "url": "",
        "features": ["邮箱验证码"],
        "is_secret": False,
    },
    {
        "key": "DIGITAL_HUMAN_API_KEY",
        "label": "数字人 API Key",
        "description": (
            "接入云端真人口播视频（如阿里百炼 wan2.2-s2v）。"
            "不配置则使用本地讲师画中画兜底。"
        ),
        "url": "",
        "features": ["数字人讲解"],
        "is_secret": True,
    },
]


# ── API Key 连通性验证 ──────────────────────────────────────────────


async def verify_api_key(key_name: str, key_value: str) -> dict:
    """验证指定 API Key 是否可用，返回 {ok, message}。

    对每个 Key 发起真实的最小化 API 探测：
    - ZHIPU / COGVIDEO: 发 max_tokens=10 的 chat/completions
    - RESEND: 调用 GET /api-keys 检查认证
    - DIGITAL_HUMAN / EMAIL_FROM: 无通用探测接口，仅检查格式
    """
    key_value = key_value.strip()
    if not key_value:
        return {"ok": False, "message": "Key 为空，请先填写后再检测"}

    try:
        if key_name == "ZHIPU_API_KEY":
            return await _verify_bigmodel_key(key_value)
        elif key_name == "COGVIDEO_API_KEY":
            return await _verify_cogvideo_key(key_value)
        elif key_name == "RESEND_API_KEY":
            return await _verify_resend_key(key_value)
        elif key_name == "DIGITAL_HUMAN_API_KEY":
            return _verify_digital_human_key(key_value)
        elif key_name == "EMAIL_FROM":
            return _verify_email_from(key_value)
        else:
            return {"ok": False, "message": f"未知的配置项: {key_name}"}
    except httpx.TimeoutException:
        logger.warning("验证 %s 超时（15s）", key_name)
        return {
            "ok": False,
            "message": (
                "检测超时：无法连接到 API 服务器。"
                "请检查：1) 网络是否连通 2) 是否需要配置代理/VPN "
                "3) 防火墙是否拦截了 HTTPS 请求"
            ),
        }
    except httpx.ConnectError as e:
        logger.warning("验证 %s 连接失败: %s", key_name, e)
        return {
            "ok": False,
            "message": "网络连接失败：无法访问 API 服务器，请检查网络设置",
        }
    except (httpx.RemoteProtocolError, httpx.ReadError) as e:
        logger.warning("验证 %s 通信异常: %s: %s", key_name, type(e).__name__, e)
        return {
            "ok": False,
            "message": "网络通信异常：连接被重置，请检查网络或稍后重试",
        }
    except Exception as e:
        logger.warning(
            "验证 %s 时异常: type=%s, msg=%s, key_value_len=%d",
            key_name,
            type(e).__name__,
            e,
            len(key_value),
        )
        return {"ok": False, "message": f"验证失败（{type(e).__name__}）: {e}"}


async def _verify_bigmodel_key(api_key: str) -> dict:
    """智谱 BigModel 平台 GLM Key 验证。"""
    url = settings.ZHIPU_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.ZHIPU_MODEL,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    logger.info("验证智谱 Key: URL=%s, model=%s", url, settings.ZHIPU_MODEL)
    async with httpx.AsyncClient(timeout=15.0, proxy=_get_proxy_url()) as client:
        resp = await client.post(url, json=payload, headers=headers)
    logger.info(
        "智谱 Key 验证响应: status=%d, body=%.300s", resp.status_code, resp.text
    )
    if resp.status_code == 200:
        return {"ok": True, "message": "智谱 API 连通，Key 有效"}
    if resp.status_code in (400, 422):
        return {"ok": True, "message": "智谱 API 认证通过，Key 有效"}
    if resp.status_code == 401:
        return {"ok": False, "message": "认证失败：Key 无效或已过期"}
    if resp.status_code == 403:
        return {"ok": False, "message": "权限不足：请检查 Key 权限设置"}
    if resp.status_code == 429:
        return {
            "ok": True,
            "message": (
                "Key 有效（智谱 API 限流中，"
                "这是 API 自身的频率限制，"
                "非本系统问题，请 1-2 分钟后重试）"
            ),
        }
    if resp.status_code in (500, 502, 503):
        return {
            "ok": False,
            "message": f"智谱服务器错误（HTTP {resp.status_code}），请稍后重试",
        }
    return {
        "ok": False,
        "message": f"API 返回 HTTP {resp.status_code}: {resp.text[:200]}",
    }


async def _verify_cogvideo_key(api_key: str) -> dict:
    """CogVideoX Key 验证 — 智谱同平台，验证 BigModel 认证 + 模型访问权限。"""
    url = settings.COGVIDEO_BASE_URL.rstrip("/") + "/videos/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.COGVIDEO_MODEL,
        "prompt": "test",
    }
    logger.info("验证 CogVideoX Key: URL=%s, model=%s", url, settings.COGVIDEO_MODEL)
    async with httpx.AsyncClient(timeout=15.0, proxy=_get_proxy_url()) as client:
        resp = await client.post(url, json=payload, headers=headers)
    logger.info(
        "CogVideoX Key 验证响应: status=%d, body=%.300s", resp.status_code, resp.text
    )
    if resp.status_code == 200:
        return {"ok": True, "message": "CogVideoX API 连通，Key 有效"}
    if resp.status_code == 401:
        return {"ok": False, "message": "认证失败：Key 无效或已过期"}
    if resp.status_code == 403:
        return {
            "ok": False,
            "message": "权限不足：该 Key 可能未开通 CogVideoX 视频生成权限",
        }
    if resp.status_code == 400:
        return {"ok": True, "message": "CogVideoX API 认证通过，Key 有效"}
    if resp.status_code == 429:
        return {"ok": True, "message": "Key 有效（智谱 API 限流中，请 1-2 分钟后重试）"}
    if resp.status_code in (500, 502, 503):
        return {
            "ok": False,
            "message": f"CogVideoX 服务器错误（HTTP {resp.status_code}），请稍后重试",
        }
    return {
        "ok": False,
        "message": f"CogVideoX API 返回 HTTP {resp.status_code}: {resp.text[:200]}",
    }


async def _verify_resend_key(api_key: str) -> dict:
    """Resend API Key 验证 — 调用 GET /me 探测认证。

    注意：Resend 受限 Key（restricted_api_key）仅能发送邮件，
    无法访问管理端点，会返回 401 但附带 restricted_api_key 标识，
    此时 Key 实际有效。
    """
    url = "https://api.resend.com/me"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    logger.info("验证 Resend Key: URL=%s", url)
    async with httpx.AsyncClient(timeout=15.0, proxy=_get_proxy_url()) as client:
        resp = await client.get(url, headers=headers)
    logger.info(
        "Resend Key 验证响应: status=%d, body=%.300s", resp.status_code, resp.text
    )
    if resp.status_code == 200:
        return {"ok": True, "message": "Resend API 连通，Key 有效"}
    if resp.status_code in (401, 403):
        # 受限 Key：仅能发邮件，管理端点返回 401 但 Key 实际有效
        if "restricted_api_key" in resp.text:
            return {"ok": True, "message": "Key 有效（受限 Key，仅可发送邮件）"}
        return {"ok": False, "message": "认证失败：Key 无效或权限不足"}
    if resp.status_code in (500, 502, 503):
        return {
            "ok": False,
            "message": f"Resend 服务器错误（HTTP {resp.status_code}），请稍后重试",
        }
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
