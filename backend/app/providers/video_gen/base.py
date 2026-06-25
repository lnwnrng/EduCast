"""视频生成 Provider 抽象基类。

三类主流视频生成 API（智谱 CogVideoX / 阿里 DashScope Kling / MiniMax Hailuo）
均为异步「提交 task → 轮询状态 → 取回 video_url → 下载」范式。本基类把
``generate()``（提交→轮询→下载落地）与 ``_download()`` 固化，子类只需实现
``submit`` / ``poll`` / ``get_result`` / ``provider_name`` / ``estimate_cost``。
"""

import asyncio
import logging
import os

import httpx

from app.config import settings
from app.providers.base import BaseProvider, ProviderResult

logger = logging.getLogger(__name__)


class VideoGenProviderBase(BaseProvider):
    """视频生成 Provider 基类（异步提交→轮询→下载）。"""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        *,
        timeout: float = 300.0,
        poll_interval: float = 5.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._poll_interval = poll_interval

    def _http_client(self, *, stream: bool = False) -> httpx.AsyncClient:
        """构造带代理/超时的 httpx 客户端。"""
        proxy = settings.HTTP_PROXY.strip() or None
        return httpx.AsyncClient(timeout=self._timeout, proxy=proxy)

    # ── 合成层便捷方法 ────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        output_path: str,
        *,
        image_url: str | None = None,
    ) -> str:
        """提交→轮询→下载生成视频到 ``output_path``，返回路径。失败抛异常。"""
        task_id = await self.submit({"prompt": prompt, "image_url": image_url})
        result = await self.get_result(task_id)
        if result.status != "completed" or not result.result_url:
            raise RuntimeError(result.error_msg or f"{self.provider_name} 生成失败")
        await self._download(result.result_url, output_path)
        logger.info("%s 生成完成: %s", self.provider_name, output_path)
        return output_path

    async def _download(self, url: str, output_path: str) -> None:
        """流式下载视频文件到本地。"""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        async with self._http_client() as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(output_path, "wb") as f:
                    async for chunk in resp.aiter_bytes():
                        f.write(chunk)

    async def get_result(self, task_id: str) -> ProviderResult:
        """轮询至终态（带超时）。子类可实现自定义 poll，本方法提供通用轮询循环。"""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout
        while True:
            result = await self.poll(task_id)
            if result.status in ("completed", "failed"):
                return result
            if loop.time() >= deadline:
                return ProviderResult(
                    task_id=task_id,
                    status="failed",
                    error_msg=f"{self.provider_name} 轮询超时（>{self._timeout:.0f}s）",
                )
            await asyncio.sleep(self._poll_interval)
