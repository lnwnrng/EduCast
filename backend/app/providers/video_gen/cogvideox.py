"""智谱 CogVideoX 文/图生视频 Provider（模块五）。

CogVideoX 与 GLM 同在智谱 BigModel 平台，走异步「提交→轮询→取回」范式：

    POST {base_url}/videos/generations   → 返回 {id, task_status}
    GET  {base_url}/async-result/{id}     → {task_status: PROCESSING|SUCCESS|FAIL,
                                              video_result: [{url, cover_image_url}]}

用于片头、概念演示等「生成式片段」分镜，按需限量 + 缓存复用以压成本。
``cogvideox-flash`` 为免费/极低价档，不接受 quality/size/fps 参数。
"""

import logging
from typing import Any

from app.config import settings
from app.providers.base import ProviderResult
from app.providers.video_gen.base import VideoGenProviderBase

logger = logging.getLogger(__name__)

# CogVideoX 异步任务终态
_STATUS_SUCCESS = "SUCCESS"
_STATUS_FAIL = "FAIL"

DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_MODEL = "cogvideox-flash"


class CogVideoXProvider(VideoGenProviderBase):
    """智谱 CogVideoX 视频生成 Provider。"""

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
        return f"cogvideox:{self._model}"

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    @property
    def _is_flash(self) -> bool:
        return "flash" in self._model.lower()

    # ── 统一 Provider 接口 ────────────────────────────────────

    async def submit(self, request: dict) -> str:
        """提交视频生成任务，返回 task_id。

        request: {"prompt": str, "image_url"?: str, 以及非 flash 档可选
        "quality"/"size"/"fps"/"duration"/"with_audio"}。
        """
        prompt = (request.get("prompt") or "").strip()
        if not prompt and not request.get("image_url"):
            raise ValueError("CogVideoX 需要 prompt 或 image_url")

        payload: dict[str, Any] = {"model": self._model, "prompt": prompt}
        if request.get("image_url"):
            payload["image_url"] = request["image_url"]
        if not self._is_flash:
            for key in ("quality", "size", "fps", "duration", "with_audio"):
                if request.get(key) is not None:
                    payload[key] = request[key]

        url = f"{self._base_url}/videos/generations"
        async with self._http_client() as client:
            resp = await client.post(url, json=payload, headers=self._headers)
        if resp.status_code != 200:
            raise RuntimeError(
                f"CogVideoX 提交失败 {resp.status_code}: {resp.text[:500]}"
            )
        data = resp.json()
        task_id = data.get("id") or data.get("request_id")
        if not task_id:
            raise RuntimeError(f"CogVideoX 响应缺少任务 id: {data}")
        logger.info("CogVideoX 已提交任务: %s", task_id)
        return str(task_id)

    async def poll(self, task_id: str) -> ProviderResult:
        """查询一次任务状态。"""
        url = f"{self._base_url}/async-result/{task_id}"
        async with self._http_client() as client:
            resp = await client.get(url, headers=self._headers)
        if resp.status_code != 200:
            raise RuntimeError(
                f"CogVideoX 轮询失败 {resp.status_code}: {resp.text[:500]}"
            )
        data = resp.json()
        status = (data.get("task_status") or "").upper()
        if status == _STATUS_SUCCESS:
            results = data.get("video_result") or []
            video_url = results[0].get("url") if results else None
            if not video_url:
                return ProviderResult(
                    task_id=task_id,
                    status="failed",
                    error_msg="CogVideoX 成功但无 video_result url",
                )
            return ProviderResult(
                task_id=task_id, status="completed", result_url=video_url
            )
        if status == _STATUS_FAIL:
            return ProviderResult(
                task_id=task_id, status="failed", error_msg="CogVideoX 任务失败"
            )
        return ProviderResult(task_id=task_id, status="processing")

    def estimate_cost(self, request: dict) -> float:
        """flash 档免费记 0；正式档按片段时长 × 费率估算（元）。"""
        if self._is_flash:
            return 0.0
        duration = float(request.get("duration_sec", settings.GEN_CLIP_SECONDS))
        return duration * settings.VIDEO_GEN_COST_PER_SEC
