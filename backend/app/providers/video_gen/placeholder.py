"""视频生成 Provider 占位 — P2 阶段实现。

P1 阶段不使用生成式视频片段。
"""

from app.providers.base import BaseProvider, ProviderResult


class PlaceholderVideoGenProvider(BaseProvider):
    """视频生成 Provider 占位实现。

    P2 阶段将替换为 CogVideoX-Flash 等真实 API。
    降级策略: CogVideoX-Flash → 通义万相 → 静态图片+转场（本实现）
    """

    @property
    def provider_name(self) -> str:
        return "placeholder_video_gen"

    async def submit(self, request: dict) -> str:
        raise NotImplementedError("视频生成 Provider P2 阶段实现")

    async def poll(self, task_id: str) -> ProviderResult:
        raise NotImplementedError("视频生成 Provider P2 阶段实现")

    async def get_result(self, task_id: str) -> ProviderResult:
        raise NotImplementedError("视频生成 Provider P2 阶段实现")

    def estimate_cost(self, request: dict) -> float:
        return 0.0
