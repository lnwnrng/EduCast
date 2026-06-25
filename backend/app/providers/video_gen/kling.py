"""Kling 可灵视频生成 Provider（经阿里云百炼 DashScope）。

DashScope 异步范式（与 CogVideoX 同为提交→轮询→取回）：

    POST {base_url}/api/v1/services/aigc/video-generation/video-synthesis
      Authorization: Bearer <api_key>
      X-DashScope-Async: enable
      body: {model, input:{prompt, media?:[{url,type}]}, parameters:{mode,
            aspect_ratio, duration, audio, watermark}}
      → {output:{task_id, task_status}}
    GET  {base_url}/api/v1/tasks/{task_id}
      → {output:{task_status: PENDING|RUNNING|SUCCEEDED|FAILED|CANCELED,
                 video_url, watermark_video_url}}

用于生成式片段分镜。需阿里云百炼 API Key（sk-xxx）。
"""

import logging
from typing import Any

from app.providers.base import ProviderResult
from app.providers.video_gen.base import VideoGenProviderBase

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com"
DEFAULT_MODEL = "kling/kling-v3-video-generation"

# DashScope 任务终态
_STATUS_SUCCESS = "SUCCEEDED"
_STATUS_FAIL = "FAILED"
_STATUS_CANCELED = "CANCELED"


class KlingProvider(VideoGenProviderBase):
    """Kling 视频生成 Provider（阿里云 DashScope 异步接口）。"""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 300.0,
        poll_interval: float = 15.0,
    ) -> None:
        super().__init__(
            api_key, model, base_url, timeout=timeout, poll_interval=poll_interval
        )

    @property
    def provider_name(self) -> str:
        return f"kling:{self._model}"

    @property
    def _headers(self) -> dict[str, str]:
        # DashScope 异步接口要求 X-DashScope-Async: enable
        return {
            "Authorization": f"Bearer {self._api_key}",
            "X-DashScope-Async": "enable",
            "Content-Type": "application/json",
        }

    # ── 统一 Provider 接口 ────────────────────────────────────

    async def submit(self, request: dict) -> str:
        """提交视频生成任务，返回 task_id。"""
        prompt = (request.get("prompt") or "").strip()
        image_url = request.get("image_url")
        if not prompt and not image_url:
            raise ValueError("Kling 需要 prompt 或 image_url")

        input_obj: dict[str, Any] = {"prompt": prompt}
        if image_url:
            input_obj["media"] = [{"url": image_url, "type": "first_frame"}]
        payload: dict[str, Any] = {
            "model": self._model,
            "input": input_obj,
            "parameters": {"mode": "std", "aspect_ratio": "16:9", "audio": False},
        }

        url = f"{self._base_url}/api/v1/services/aigc/video-generation/video-synthesis"
        async with self._http_client() as client:
            resp = await client.post(url, json=payload, headers=self._headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Kling 提交失败 {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        output = data.get("output") or {}
        task_id = output.get("task_id")
        if not task_id:
            raise RuntimeError(f"Kling 响应缺少 task_id: {data}")
        logger.info("Kling 已提交任务: %s", task_id)
        return str(task_id)

    async def poll(self, task_id: str) -> ProviderResult:
        """查询一次任务状态。"""
        url = f"{self._base_url}/api/v1/tasks/{task_id}"
        # 查询无需 X-DashScope-Async
        query_headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with self._http_client() as client:
            resp = await client.get(url, headers=query_headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Kling 轮询失败 {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        output = data.get("output") or {}
        status = (output.get("task_status") or "").upper()
        if status == _STATUS_SUCCESS:
            video_url = output.get("video_url") or output.get("watermark_video_url")
            if not video_url:
                return ProviderResult(
                    task_id=task_id,
                    status="failed",
                    error_msg="Kling 成功但无 video_url",
                )
            return ProviderResult(
                task_id=task_id, status="completed", result_url=video_url
            )
        if status in (_STATUS_FAIL, _STATUS_CANCELED):
            return ProviderResult(
                task_id=task_id,
                status="failed",
                error_msg=f"Kling 任务{status}",
            )
        return ProviderResult(task_id=task_id, status="processing")

    def estimate_cost(self, request: dict) -> float:
        """按片段时长 × 费率估算（元）。"""
        duration = float(request.get("duration_sec", 5.0))
        return duration * 1.0
