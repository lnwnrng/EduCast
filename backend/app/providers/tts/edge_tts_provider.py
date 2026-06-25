"""Edge-TTS Provider — 微软在线免费 TTS，毕设首选配音方案（成本为 0）。

Edge-TTS 为同步「一次调用即出音频」模式，因此 ``submit`` 直接执行合成并缓存
结果，``poll``/``get_result`` 取回缓存。核心方法 ``synthesize`` 供
CompositionService 逐分镜直接调用（便于失败时降级为静音分镜）。
"""

import logging
import os
import uuid

from app.config import settings
from app.pipeline.ssml_converter import has_markers, narration_to_ssml
from app.providers.base import BaseProvider, ProviderResult

logger = logging.getLogger(__name__)


class EdgeTTSProvider(BaseProvider):
    """Edge-TTS Provider — 免费配音。"""

    def __init__(self, voice: str | None = None) -> None:
        self._voice = voice or settings.EDGE_TTS_VOICE
        # submit / get_result 之间缓存结果（带 TTL 淘汰，防止内存泄漏）
        self._results: dict[str, ProviderResult] = {}
        self._results_order: list[str] = []
        self._max_cache_size = 200  # 最多缓存 200 个结果

    @property
    def provider_name(self) -> str:
        return "edge_tts"

    async def synthesize(
        self,
        text: str,
        output_path: str,
        *,
        voice: str | None = None,
    ) -> str:
        """把文本合成为音频文件并返回路径。

        惰性导入 ``edge_tts``，便于测试 monkeypatch 与避免无网络环境导入开销。

        若讲稿含 SSML 语音标记（``[PAUSE:N]`` / ``[EMPHASIS]`` / ``[SLOW]``，
        由 ScriptWriter 多智能体管道插入），先经 ``narration_to_ssml`` 转换为
        Edge-TTS 兼容 SSML 再合成，使配音具备停顿/重音/缓讲韵律。无标记时
        走纯文本路径，行为与原先一致。
        """
        import edge_tts

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        effective_voice = voice or self._voice
        if has_markers(text):
            payload = narration_to_ssml(text, effective_voice)
            # SSML 文档自带 <voice> 标签，传 voice 仅作占位（被 SSML 覆盖）
            communicate = edge_tts.Communicate(payload, effective_voice)
        else:
            communicate = edge_tts.Communicate(text, effective_voice)
        await communicate.save(output_path)
        logger.info("Edge-TTS 合成完成: %s", output_path)
        return output_path

    async def submit(self, request: dict) -> str:
        """提交 TTS 合成请求。

        request 需包含: ``text``、``output_path``；可选 ``voice``。
        成功缓存结果并返回 task_id；失败抛异常交由 Router/上层降级。
        """
        text = request.get("text", "")
        output_path = request["output_path"]
        await self.synthesize(text, output_path, voice=request.get("voice"))
        task_id = str(uuid.uuid4())
        result = ProviderResult(
            task_id=task_id,
            status="completed",
            result_url=output_path,
            cost=0.0,
        )
        self._results[task_id] = result
        self._results_order.append(task_id)
        while len(self._results_order) > self._max_cache_size:
            old_id = self._results_order.pop(0)
            self._results.pop(old_id, None)
        return task_id

    async def poll(self, task_id: str) -> ProviderResult:
        """Edge-TTS 为同步生成，poll 直接返回缓存结果。"""
        return await self.get_result(task_id)

    async def get_result(self, task_id: str) -> ProviderResult:
        """获取生成结果。"""
        result = self._results.get(task_id)
        if result is None:
            return ProviderResult(
                task_id=task_id,
                status="failed",
                error_msg=f"未找到任务 {task_id} 的结果",
            )
        return result

    def estimate_cost(self, request: dict) -> float:
        """Edge-TTS 免费，成本为 0。"""
        return 0.0
