"""Edge-TTS Provider — P1 阶段实现。

Edge-TTS 为微软在线免费 TTS 服务，是毕设首选配音方案。
"""

from app.providers.base import BaseProvider, ProviderResult


class EdgeTTSProvider(BaseProvider):
    """Edge-TTS Provider — 免费配音。

    TODO(P1): 实现基于 edge-tts 库的配音生成。
    """

    @property
    def provider_name(self) -> str:
        return "edge_tts"

    async def submit(self, request: dict) -> str:
        """提交 TTS 合成请求。

        request 应包含:
            text (str): 朗读文本
            voice (str): 音色名称
            output_path (str): 输出文件路径
        """
        # TODO: 使用 edge-tts 库生成音频
        raise NotImplementedError("EdgeTTSProvider.submit 待实现")

    async def poll(self, task_id: str) -> ProviderResult:
        """Edge-TTS 为同步生成，poll 直接返回结果。"""
        raise NotImplementedError("EdgeTTSProvider.poll 待实现")

    async def get_result(self, task_id: str) -> ProviderResult:
        """获取生成结果。"""
        raise NotImplementedError("EdgeTTSProvider.get_result 待实现")

    def estimate_cost(self, request: dict) -> float:
        """Edge-TTS 免费，成本为 0。"""
        return 0.0
