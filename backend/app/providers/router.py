"""Provider 路由器 — 降级链管理与自动切换。"""

import logging

from app.providers.base import BaseProvider, ProviderResult, RoutingStrategy

logger = logging.getLogger(__name__)


class ProviderRouter:
    """Provider 路由器。

    按策略选择 Provider，首选失败自动切换到备选（降级链）。
    """

    def __init__(
        self,
        providers: list[BaseProvider],
        strategy: RoutingStrategy = RoutingStrategy.FREE_FIRST,
    ) -> None:
        self._providers = providers
        self._strategy = strategy

    async def execute(self, request: dict) -> ProviderResult:
        """执行请求 — 按降级链逐个尝试。"""
        last_error: Exception | None = None

        for provider in self._select_providers():
            try:
                logger.info("尝试 Provider: %s", provider.provider_name)
                task_id = await provider.submit(request)
                result = await provider.get_result(task_id)
                logger.info(
                    "Provider %s 成功，费用: %.4f",
                    provider.provider_name,
                    result.cost,
                )
                return result
            except Exception as exc:
                logger.warning(
                    "Provider %s 失败: %s，尝试降级",
                    provider.provider_name,
                    exc,
                )
                last_error = exc

        # 所有 Provider 均失败
        return ProviderResult(
            task_id="",
            status="failed",
            error_msg=f"所有 Provider 均失败: {last_error}",
        )

    def estimate_total_cost(self, request: dict) -> float:
        """使用首选 Provider 预估成本。"""
        providers = self._select_providers()
        if providers:
            return providers[0].estimate_cost(request)
        return 0.0

    def _select_providers(self) -> list[BaseProvider]:
        """按策略排序 Provider 列表。"""
        if self._strategy == RoutingStrategy.FREE_FIRST:
            return sorted(
                self._providers,
                key=lambda p: p.estimate_cost({}),
            )
        # 其他策略暂按原序返回
        return list(self._providers)
