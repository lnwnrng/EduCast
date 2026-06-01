"""智谱 GLM-4-Flash LLM Provider — P1 阶段实现。"""

from app.providers.base import BaseProvider, ProviderResult


class ZhipuLLMProvider(BaseProvider):
    """智谱 GLM-4-Flash Provider。

    免费档，用于脚本编排、分镜规划、出题、合规审核。

    TODO(P1): 实现 submit/poll/get_result
    """

    @property
    def provider_name(self) -> str:
        return "zhipu_glm4_flash"

    async def submit(self, request: dict) -> str:
        """提交 LLM 生成请求。"""
        # TODO: 接入智谱 API
        raise NotImplementedError("ZhipuLLMProvider.submit 待实现")

    async def poll(self, task_id: str) -> ProviderResult:
        """轮询任务状态。"""
        raise NotImplementedError("ZhipuLLMProvider.poll 待实现")

    async def get_result(self, task_id: str) -> ProviderResult:
        """获取生成结果。"""
        raise NotImplementedError("ZhipuLLMProvider.get_result 待实现")

    def estimate_cost(self, request: dict) -> float:
        """GLM-4-Flash 免费档，成本为 0。"""
        return 0.0
