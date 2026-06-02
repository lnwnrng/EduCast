"""数字人 Provider 占位 — P2 阶段实现。

P1 阶段降级为"纯旁白 + 课件"模式。
"""

from app.config import settings
from app.providers.base import BaseProvider, ProviderResult


class PlaceholderDigitalHumanProvider(BaseProvider):
    """数字人 Provider 占位实现。

    P2 阶段将替换为智影/蝉镜等真实 API。
    降级策略: 智影 → HeyGem → 纯旁白+课件（本实现）
    """

    @property
    def provider_name(self) -> str:
        return "placeholder_digital_human"

    async def submit(self, request: dict) -> str:
        raise NotImplementedError("数字人 Provider P2 阶段实现")

    async def poll(self, task_id: str) -> ProviderResult:
        raise NotImplementedError("数字人 Provider P2 阶段实现")

    async def get_result(self, task_id: str) -> ProviderResult:
        raise NotImplementedError("数字人 Provider P2 阶段实现")

    def estimate_cost(self, request: dict) -> float:
        """按预估口播时长 × 费率估算（元）。request: {"duration_sec": float}。"""
        duration = float(request.get("duration_sec", 0.0))
        return duration * settings.DIGITAL_HUMAN_COST_PER_SEC
