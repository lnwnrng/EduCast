"""视频生成 Provider 子包（模块五）— 多模型管理（cc-switch 风格）。

支持智谱 CogVideoX / 阿里 DashScope Kling / MiniMax Hailuo 三类主流视频生成
模型，外加可编辑 base_url/model 的自定义入口。管理员在「LLM 管理 → 视频生成」
页面配置 DB 中的 provider 实例并激活一条；保存/激活时镜像到运行时设置
（VIDEO_GEN_*），供合成层同步路径 `get_video_gen_provider()` 直接取用，无需
改 composition 为 async。无 DB 配置时回退 COGVIDEO_API_KEY / 镜像的 ZHIPU_API_KEY
（CogVideoX），保留「无 Key 也能跑 / 自动降级本地运镜」。
"""

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.providers.video_gen.base import VideoGenProviderBase
from app.providers.video_gen.cogvideox import (
    DEFAULT_BASE_URL as COGVIDEO_DEFAULT_BASE_URL,
)
from app.providers.video_gen.cogvideox import DEFAULT_MODEL as COGVIDEO_DEFAULT_MODEL
from app.providers.video_gen.cogvideox import CogVideoXProvider
from app.providers.video_gen.kling import DEFAULT_BASE_URL as KLING_DEFAULT_BASE_URL
from app.providers.video_gen.kling import DEFAULT_MODEL as KLING_DEFAULT_MODEL
from app.providers.video_gen.kling import KlingProvider
from app.providers.video_gen.minimax import DEFAULT_BASE_URL as MINIMAX_DEFAULT_BASE_URL
from app.providers.video_gen.minimax import DEFAULT_MODEL as MINIMAX_DEFAULT_MODEL
from app.providers.video_gen.minimax import MiniMaxProvider
from app.schemas.llm import ProviderMeta, ProviderModelInfo
from app.services.settings_service import (
    get_effective_key,
    get_effective_value,
    set_runtime_setting,
)

if TYPE_CHECKING:
    from app.models.video_gen_provider import VideoGenProviderConfig

logger = logging.getLogger(__name__)


# ── 运行时镜像键 ───────────────────────────────────────

#: 视频生成激活配置的运行时镜像键（供同步 get_video_gen_provider 读取）。
RUNTIME_KEYS = {
    "type": "VIDEO_GEN_PROVIDER_TYPE",
    "key": "VIDEO_GEN_API_KEY",
    "base_url": "VIDEO_GEN_BASE_URL",
    "model": "VIDEO_GEN_MODEL",
}


def _models(*ids: str) -> list[ProviderModelInfo]:
    return [ProviderModelInfo(model_id=i, label=i) for i in ids]


VIDEO_GEN_REGISTRY: dict[str, ProviderMeta] = {
    "cogvideox": ProviderMeta(
        provider_type="cogvideox",
        label="智谱 CogVideoX",
        icon_key="cogvideox",
        default_base_url=COGVIDEO_DEFAULT_BASE_URL,
        default_model=COGVIDEO_DEFAULT_MODEL,
        models=_models("cogvideox-flash", "cogvideox", "cogvideox-2"),
        key_label="智谱 API Key",
        key_url="https://open.bigmodel.cn",
    ),
    "kling": ProviderMeta(
        provider_type="kling",
        label="可灵 Kling",
        icon_key="kling",
        default_base_url=KLING_DEFAULT_BASE_URL,
        default_model=KLING_DEFAULT_MODEL,
        models=_models(
            "kling/kling-v3-video-generation",
            "kling/kling-v3-omni-video-generation",
        ),
        key_label="阿里云百炼 API Key",
        key_url="https://bailian.console.aliyun.com",
    ),
    "minimax": ProviderMeta(
        provider_type="minimax",
        label="MiniMax 海螺",
        icon_key="minimax",
        default_base_url=MINIMAX_DEFAULT_BASE_URL,
        default_model=MINIMAX_DEFAULT_MODEL,
        models=_models(
            "MiniMax-Hailuo-2.3-Fast",
            "MiniMax-Hailuo-2.3",
            "MiniMax-Hailuo-02",
        ),
        key_label="MiniMax API Key",
        key_url="https://platform.minimax.io",
    ),
}

_VIDEO_GEN_CLASS: dict[str, type[VideoGenProviderBase]] = {
    "cogvideox": CogVideoXProvider,
    "kling": KlingProvider,
    "minimax": MiniMaxProvider,
}


def build_video_gen_provider_from_config(
    config: "VideoGenProviderConfig",
) -> VideoGenProviderBase | None:
    """根据一条 DB 配置构造视频生成 provider。未知类型返回 None。"""
    meta = VIDEO_GEN_REGISTRY.get(config.provider_type)
    cls = _VIDEO_GEN_CLASS.get(config.provider_type)
    if meta is None or cls is None:
        logger.warning("未知视频生成 provider_type: %s", config.provider_type)
        return None
    model = (config.model_id or meta.default_model).strip() or meta.default_model
    base_url = (
        config.base_url or meta.default_base_url
    ).strip() or meta.default_base_url
    return cls(
        api_key=config.api_key,
        model=model,
        base_url=base_url,
        timeout=settings.VIDEO_GEN_TIMEOUT,
        poll_interval=settings.VIDEO_GEN_POLL_INTERVAL,
    )


async def _get_active_video_gen_config(
    db: AsyncSession,
) -> "VideoGenProviderConfig | None":
    """读取激活（is_active=True）的视频生成配置。"""
    from app.models.video_gen_provider import VideoGenProviderConfig

    result = await db.execute(
        select(VideoGenProviderConfig)
        .where(VideoGenProviderConfig.is_active.is_(True))
        .where(VideoGenProviderConfig.is_enabled.is_(True))
        .where(VideoGenProviderConfig.deleted_at.is_(None))
        .limit(1)
    )
    return result.scalars().one_or_none()


async def resync_video_gen_mirror(db: AsyncSession) -> None:
    """把激活的视频生成配置镜像到运行时 VIDEO_GEN_*。

    使「LLM 管理 → 视频生成」成为视频生成 provider 的唯一配置入口：
    合成层 ``get_video_gen_provider()`` 仍为同步函数，直接读运行时镜像构造
    对应类型的 provider，无需改 composition 为 async。无激活配置时清除镜像。
    """
    cfg = await _get_active_video_gen_config(db)
    if cfg is None:
        set_runtime_setting(RUNTIME_KEYS["type"], None)
        set_runtime_setting(RUNTIME_KEYS["key"], None)
        set_runtime_setting(RUNTIME_KEYS["base_url"], None)
        set_runtime_setting(RUNTIME_KEYS["model"], None)
        return
    set_runtime_setting(RUNTIME_KEYS["type"], cfg.provider_type)
    set_runtime_setting(RUNTIME_KEYS["key"], cfg.api_key)
    set_runtime_setting(RUNTIME_KEYS["base_url"], cfg.base_url)
    set_runtime_setting(RUNTIME_KEYS["model"], cfg.model_id)


def get_video_gen_provider() -> VideoGenProviderBase | None:
    """构造视频生成 provider（同步，读运行时镜像 + 旧 env 回退）。

    优先用「LLM 管理 → 视频生成」激活配置镜像的 VIDEO_GEN_*；为空时回退
    COGVIDEO_API_KEY（旧系统设置项）→ 镜像的 ZHIPU_API_KEY（CogVideoX 与
    GLM 同 Key），构造 CogVideoXProvider。全部为空返回 None，合成层走
    Ken-Burns 本地兜底。
    """
    ptype = get_effective_value(RUNTIME_KEYS["type"], "cogvideox") or "cogvideox"
    api_key = (
        get_effective_key(RUNTIME_KEYS["key"])
        or get_effective_key("COGVIDEO_API_KEY")
        or get_effective_key("ZHIPU_API_KEY")
    )
    if not api_key:
        return None

    meta = VIDEO_GEN_REGISTRY.get(ptype) or VIDEO_GEN_REGISTRY["cogvideox"]
    cls = _VIDEO_GEN_CLASS.get(ptype, CogVideoXProvider)
    base_url = (
        get_effective_value(RUNTIME_KEYS["base_url"], "") or meta.default_base_url
    )
    model = get_effective_value(RUNTIME_KEYS["model"], "") or meta.default_model
    return cls(
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout=settings.VIDEO_GEN_TIMEOUT,
        poll_interval=settings.VIDEO_GEN_POLL_INTERVAL,
    )


__all__ = [
    "VIDEO_GEN_REGISTRY",
    "build_video_gen_provider_from_config",
    "get_video_gen_provider",
    "resync_video_gen_mirror",
    "CogVideoXProvider",
    "KlingProvider",
    "MiniMaxProvider",
]
