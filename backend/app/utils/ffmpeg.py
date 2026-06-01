"""FFmpeg 命令构建与执行工具。

使用 Builder 模式构建 FFmpeg 命令，避免手写 shell 字符串拼接。
"""

import asyncio
import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


class FFmpegCommand:
    """FFmpeg 命令构建器 — Builder 模式。

    使用示例:
        cmd = (
            FFmpegCommand()
            .add_input("background.mp4")
            .add_input("narrator.mp3")
            .set_codec()
            .set_resolution()
            .add_subtitle("subtitles.srt")
            .set_output("output.mp4")
        )
        output_path = await cmd.run()
    """

    def __init__(self) -> None:
        self._inputs: list[str] = []
        self._filters: list[str] = []
        self._output: Optional[str] = None
        self._video_codec: str = "libx264"
        self._audio_codec: str = "aac"
        self._audio_bitrate: str = "128k"
        self._preset: str = "medium"
        self._width: int = 1920
        self._height: int = 1080
        self._fps: int = 30
        self._extra_args: list[str] = []

    def add_input(self, path: str) -> "FFmpegCommand":
        """添加输入文件。"""
        self._inputs.append(path)
        return self

    def set_output(self, path: str) -> "FFmpegCommand":
        """设置输出文件路径。"""
        self._output = path
        return self

    def add_filter(self, filter_str: str) -> "FFmpegCommand":
        """添加视频滤镜。"""
        self._filters.append(filter_str)
        return self

    def add_subtitle(self, srt_path: str) -> "FFmpegCommand":
        """添加字幕叠加。"""
        self._filters.append(f"subtitles={srt_path}")
        return self

    def add_watermark(
        self,
        image_path: str,
        position: str = "10:10",
    ) -> "FFmpegCommand":
        """添加水印。"""
        self._filters.append(
            f"movie={image_path}[wm];[in][wm]overlay={position}"
        )
        return self

    def set_codec(
        self,
        video: str = "libx264",
        audio: str = "aac",
    ) -> "FFmpegCommand":
        """设置编解码器。"""
        self._video_codec = video
        self._audio_codec = audio
        return self

    def set_resolution(
        self, width: int = 1920, height: int = 1080
    ) -> "FFmpegCommand":
        """设置输出分辨率。"""
        self._width = width
        self._height = height
        return self

    def build(self) -> list[str]:
        """构建 FFmpeg 命令参数列表。"""
        if not self._output:
            raise ValueError("必须设置输出文件路径")

        cmd = ["ffmpeg", "-y"]

        # 输入
        for inp in self._inputs:
            cmd.extend(["-i", inp])

        # 滤镜
        if self._filters:
            cmd.extend(["-vf", ",".join(self._filters)])

        # 编码
        cmd.extend([
            "-c:v", self._video_codec,
            "-preset", self._preset,
            "-c:a", self._audio_codec,
            "-b:a", self._audio_bitrate,
            "-r", str(self._fps),
            "-s", f"{self._width}x{self._height}",
        ])

        # 额外参数
        cmd.extend(self._extra_args)

        # 输出
        cmd.append(self._output)

        return cmd

    async def run(self) -> str:
        """异步执行 FFmpeg 命令，返回输出路径。"""
        cmd = self.build()
        logger.info("执行 FFmpeg: %s", " ".join(cmd))

        def _run() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

        try:
            result = await asyncio.to_thread(_run)
            logger.info("FFmpeg 执行成功: %s", self._output)
            return self._output  # type: ignore[return-value]
        except subprocess.CalledProcessError as exc:
            logger.error("FFmpeg 执行失败: %s", exc.stderr)
            raise
