"""MiniMax 海螺（Hailuo）视频生成 Provider。

异步范式：

    POST {base_url}/v1/video_generation
      Authorization: Bearer <api_key>
      body: {model, first_frame_image, prompt?, duration?, resolution?}
      → {task_id, base_resp:{status_code, status_msg}}
    GET  {base_url}/v1/query/video_generation?task_id={task_id}
      → {status: processing|success|failed, file_id, download_url?}
    （若仅返回 file_id）GET {base_url}/v1/files/retrieve?file_id={file_id}
      → {file:{download_url, ...}}

用于生成式片段分镜。需 MiniMax 平台 API Key。
"""

import logging
from typing import Any

from app.providers.base import ProviderResult
from app.providers.video_gen.base import VideoGenProviderBase

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.minimax.io"
DEFAULT_MODEL = "MiniMax-Hailuo-2.3-Fast"

# MiniMax 任务状态
_STATUS_SUCCESS = "success"
_STATUS_FAIL = "failed"


class MiniMaxProvider(VideoGenProviderBase):
    """MiniMax Hailuo 视频生成 Provider（异步提交→轮询→取回）。"""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 300.0,
        poll_interval: float = 5.0,
    ) -> None:
        super().__init__(
            api_key, model, base_url, timeout=timeout, poll_interval=poll_interval
        )

    @property
    def provider_name(self) -> str:
        return f"minimax:{self._model}"

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    # ── 统一 Provider 接口 ────────────────────────────────────

    async def submit(self, request: dict) -> str:
        """提交视频生成任务，返回 task_id。

        MiniMax 图生视频要求 first_frame_image；文生视频同样走该端点，
        无图时传一个空 first_frame_image 并依赖 prompt（部分型号支持纯文生）。
        """
        prompt = (request.get("prompt") or "").strip()
        image_url = request.get("image_url")
        if not prompt and not image_url:
            raise ValueError("MiniMax 需要 prompt 或 image_url")

        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "first_frame_image": image_url or "",
        }
        url = f"{self._base_url}/v1/video_generation"
        async with self._http_client() as client:
            resp = await client.post(url, json=payload, headers=self._headers)
        if resp.status_code != 200:
            raise RuntimeError(
                f"MiniMax 提交失败 {resp.status_code}: {resp.text[:500]}"
            )
        data = resp.json()
        task_id = data.get("task_id")
        if not task_id:
            raise RuntimeError(f"MiniMax 响应缺少 task_id: {data}")
        logger.info("MiniMax 已提交任务: %s", task_id)
        return str(task_id)

    async def poll(self, task_id: str) -> ProviderResult:
        """查询一次任务状态；成功时按需再取 file download_url。"""
        url = f"{self._base_url}/v1/query/video_generation"
        params = {"task_id": task_id}
        async with self._http_client() as client:
            resp = await client.get(url, params=params, headers=self._headers)
        if resp.status_code != 200:
            raise RuntimeError(
                f"MiniMax 轮询失败 {resp.status_code}: {resp.text[:500]}"
            )
        data = resp.json()
        status = (data.get("status") or "").lower()
        if status == _STATUS_SUCCESS:
            video_url = data.get("download_url")
            if not video_url:
                file_id = data.get("file_id")
                if file_id:
                    video_url = await self._retrieve_file_url(file_id)
            if not video_url:
                return ProviderResult(
                    task_id=task_id,
                    status="failed",
                    error_msg="MiniMax 成功但无 download_url/file_id",
                )
            return ProviderResult(
                task_id=task_id, status="completed", result_url=video_url
            )
        if status == _STATUS_FAIL:
            return ProviderResult(
                task_id=task_id, status="failed", error_msg="MiniMax 任务失败"
            )
        return ProviderResult(task_id=task_id, status="processing")

    async def _retrieve_file_url(self, file_id: str) -> str | None:
        """通过 file_id 取回下载地址。"""
        url = f"{self._base_url}/v1/files/retrieve"
        params = {"file_id": file_id}
        try:
            async with self._http_client() as client:
                resp = await client.get(url, params=params, headers=self._headers)
            if resp.status_code != 200:
                return None
            data = resp.json()
            file_obj = data.get("file") or {}
            return file_obj.get("download_url")
        except Exception:  # noqa: BLE001 — file 取回失败不阻断，上层记 failed
            return None

    def estimate_cost(self, request: dict) -> float:
        """按片段时长 × 费率估算（元）。"""
        duration = float(request.get("duration_sec", 5.0))
        return duration * 1.0
