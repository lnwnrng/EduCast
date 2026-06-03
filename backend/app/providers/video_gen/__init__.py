"""视频生成 Provider 子包（模块五）。"""

from app.config import settings
from app.providers.video_gen.cogvideox import CogVideoXProvider


def get_video_gen_provider() -> CogVideoXProvider | None:
    """构造默认视频生成 Provider（智谱 CogVideoX）。

    优先用 ``COGVIDEO_API_KEY``；为空时回退 ``ZHIPU_API_KEY``（CogVideoX 与 GLM
    同平台同 Key）。两者皆空时返回 None，合成层据此走本地 Ken-Burns 兜底。
    """
    api_key = settings.COGVIDEO_API_KEY or settings.ZHIPU_API_KEY
    if not api_key:
        return None
    return CogVideoXProvider(
        api_key=api_key,
        model=settings.COGVIDEO_MODEL,
        base_url=settings.COGVIDEO_BASE_URL,
        timeout=settings.VIDEO_GEN_TIMEOUT,
        poll_interval=settings.VIDEO_GEN_POLL_INTERVAL,
    )


__all__ = ["CogVideoXProvider", "get_video_gen_provider"]
