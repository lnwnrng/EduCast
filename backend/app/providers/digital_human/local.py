"""数字人本地兜底 Provider（模块四）。

无云端 API Key 时使用：渲染一张静态讲师头像作前景，由合成层 ``overlay_pip_clip``
叠加到课件底图上，配合旁白做「讲师画中画」——非真口型，是诚实的占位讲师，保证
``digital_human`` 分镜在零成本下仍有讲师临场感。

真机云 API（腾讯云数智人 / HeyGen / 硅基 DUIX）到位后，由独立 vendor Provider 按
``DIGITAL_HUMAN_API_KEY`` 热插拔接管（实现 ``generate`` 取回口播视频作前景），合成层
与成本护栏零改动。
"""

import logging

from app.config import settings
from app.providers.base import BaseProvider, ProviderResult

logger = logging.getLogger(__name__)


class LocalDigitalHumanProvider(BaseProvider):
    """本地讲师头像前景 Provider（零成本兜底）。

    非异步任务式：核心方法 ``render_foreground`` 直接产出透明底头像 PNG。
    submit/poll/get_result 仅为满足统一接口，本地路径不走它们。
    """

    def __init__(self, renderer=None) -> None:
        self._renderer = renderer

    @property
    def provider_name(self) -> str:
        return "local_digital_human"

    def _get_renderer(self):
        """惰性构造 SlideRenderer（避免 providers→pipeline 的导入期耦合）。"""
        if self._renderer is None:
            from app.pipeline.renderer import SlideRenderer

            self._renderer = SlideRenderer()
        return self._renderer

    async def render_foreground(
        self, output_path: str, *, name: str | None = None
    ) -> str:
        """渲染本地讲师头像前景（透明底 PNG），返回路径。"""
        avatar_name = name or settings.DIGITAL_HUMAN_AVATAR_NAME
        return self._get_renderer().render_avatar(
            name=avatar_name, output_path=output_path
        )

    # ── 统一 Provider 接口（本地不走异步任务式）──────────────

    async def submit(self, request: dict) -> str:
        raise NotImplementedError("本地数字人为渲染式，请用 render_foreground")

    async def poll(self, task_id: str) -> ProviderResult:
        raise NotImplementedError("本地数字人为渲染式，请用 render_foreground")

    async def get_result(self, task_id: str) -> ProviderResult:
        raise NotImplementedError("本地数字人为渲染式，请用 render_foreground")

    def estimate_cost(self, request: dict) -> float:
        """本地兜底零成本。"""
        return 0.0
