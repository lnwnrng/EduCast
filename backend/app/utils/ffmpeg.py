"""FFmpeg 命令构建与执行工具。

提供两类能力：
- ``FFmpegCommand``：Builder 模式构建单输入滤镜命令（水印/字幕硬嵌等）。
- 模块级合成助手（``probe_duration`` / ``image_audio_to_clip`` /
  ``concat_clips`` / ``mux_subtitle_and_chapters``）：模块三逐镜合成所需的
  原子操作。全部经单一 ``_run`` 执行，便于单元测试 monkeypatch，避免对真实
  FFmpeg 的依赖。
"""

import asyncio
import logging
import os
import subprocess

from app.config import settings

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
        self._output: str | None = None
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
        self._filters.append(f"movie={image_path}[wm];[in][wm]overlay={position}")
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

    def set_resolution(self, width: int = 1920, height: int = 1080) -> "FFmpegCommand":
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
        cmd.extend(
            [
                "-c:v",
                self._video_codec,
                "-preset",
                self._preset,
                "-c:a",
                self._audio_codec,
                "-b:a",
                self._audio_bitrate,
                "-r",
                str(self._fps),
                "-s",
                f"{self._width}x{self._height}",
            ]
        )

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
            await asyncio.to_thread(_run)
            logger.info("FFmpeg 执行成功: %s", self._output)
            return self._output  # type: ignore[return-value]
        except subprocess.CalledProcessError as exc:
            logger.error("FFmpeg 执行失败: %s", exc.stderr)
            raise


# ── 模块级合成助手 ───────────────────────────────────────────
#
# 这些函数是模块三逐镜合成的原子操作。它们是仅有的真正调用外部
# ffmpeg/ffprobe 二进制的地方；上层（VideoComposer / CompositionService）
# 通过它们间接合成，单元测试可对本模块函数做 monkeypatch 以脱离真实 FFmpeg。


async def _run(args: list[str]) -> str:
    """执行外部命令，返回 stdout（失败抛 CalledProcessError）。"""
    logger.info("执行: %s", " ".join(args))

    def _exec() -> subprocess.CompletedProcess[str]:
        # 显式 UTF-8 解码：ffmpeg 横幅含非本地编码字节，Windows 默认 gbk 会报错
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )

    proc = await asyncio.to_thread(_exec)
    return proc.stdout


async def probe_duration(path: str) -> float:
    """用 ffprobe 读取媒体时长（秒）；失败或无法解析时返回 0.0。"""
    try:
        out = await _run(
            [
                settings.FFPROBE_BIN,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ]
        )
        return float(out.strip())
    except (subprocess.CalledProcessError, ValueError) as exc:
        logger.warning("ffprobe 读取时长失败 (%s): %s", path, exc)
        return 0.0


async def image_audio_to_clip(
    image_path: str,
    audio_path: str | None,
    output_path: str,
    *,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    duration: float | None = None,
) -> str:
    """由静态图（+可选旁白音频）生成单分镜 MP4。

    始终编码为统一参数（libx264/yuv420p + aac 128k + 指定 WxH/fps），并保证
    含一条音频流，以便后续用 concat demuxer 无损拼接。

    - 有 ``audio_path``：时长 = 音频时长（``-shortest``）。
    - 无音频：用 ``anullsrc`` 生成静音轨，时长取 ``duration``（兜底 4 秒）。
    """
    vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
    vf += f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1"

    args = [settings.FFMPEG_BIN, "-y", "-loop", "1", "-i", image_path]

    if audio_path:
        args += ["-i", audio_path]
        tail = ["-shortest"]
    else:
        args += [
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
        ]
        tail = ["-t", str(duration if duration and duration > 0 else 4.0)]

    args += [
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        *tail,
        output_path,
    ]
    await _run(args)
    return output_path


async def concat_clips(clip_paths: list[str], output_path: str) -> str:
    """用 concat demuxer 无损拼接多个同参数 MP4 片段。"""
    if not clip_paths:
        raise ValueError("没有可拼接的片段")

    list_path = f"{output_path}.concat.txt"
    lines = []
    for p in clip_paths:
        # concat 列表用单引号包裹路径；统一正斜杠，转义内部单引号
        safe = os.path.abspath(p).replace("\\", "/").replace("'", "'\\''")
        lines.append(f"file '{safe}'")
    with open(list_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    try:
        await _run(
            [
                settings.FFMPEG_BIN,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_path,
                "-c",
                "copy",
                output_path,
            ]
        )
    finally:
        if os.path.exists(list_path):
            os.remove(list_path)
    return output_path


async def mux_subtitle_and_chapters(
    video_path: str,
    output_path: str,
    *,
    srt_path: str | None = None,
    chapter_metadata_path: str | None = None,
) -> str:
    """为成片复用软字幕（mov_text）与章节 metadata（均为可选）。"""
    args = [settings.FFMPEG_BIN, "-y", "-i", video_path]

    # 输入索引：0=视频；按需追加 章节metadata / 字幕
    meta_idx: int | None = None
    sub_idx: int | None = None
    next_idx = 1
    if chapter_metadata_path:
        args += ["-f", "ffmetadata", "-i", chapter_metadata_path]
        meta_idx = next_idx
        next_idx += 1
    if srt_path:
        args += ["-i", srt_path]
        sub_idx = next_idx
        next_idx += 1

    args += ["-map", "0"]
    if sub_idx is not None:
        args += ["-map", str(sub_idx)]
    args += ["-map_metadata", str(meta_idx) if meta_idx is not None else "0"]
    args += ["-c", "copy"]
    if sub_idx is not None:
        args += ["-c:s", "mov_text"]
    args += [output_path]

    await _run(args)
    return output_path
