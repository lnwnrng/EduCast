"""TTS Provider 子包。"""

from app.config import settings
from app.providers.tts.edge_tts_provider import EdgeTTSProvider


def get_tts_provider() -> EdgeTTSProvider:
    """构造默认 TTS Provider。

    Edge-TTS 免费且无需 API Key，故始终返回可用 Provider。
    """
    return EdgeTTSProvider(voice=settings.EDGE_TTS_VOICE)


__all__ = ["EdgeTTSProvider", "get_tts_provider"]
