"""FFmpeg 视频合成器 — 把逐分镜片段拼接为最终教学视频。

职责很薄：调用 ``app.utils.ffmpeg`` 的原子操作完成「拼接 → 复用字幕/章节」。
逐分镜片段（静图+旁白）由 CompositionService 预先生成；字幕已烤进画面，这里
另把 SRT 作为软字幕、章节作为 metadata 复用进 MP4。

合成规格（来自 pipeline-orchestration SKILL）:
- 分辨率 1920×1080 / 编码 H.264+AAC / 帧率 30fps
- 字幕 SRT（软）+ 章节 FFmpeg metadata
"""

import logging
import os

from app.utils import ffmpeg

logger = logging.getLogger(__name__)


class VideoComposer:
    """FFmpeg 视频合成器。"""

    async def compose(
        self,
        clip_paths: list[str],
        output_path: str,
        *,
        srt_path: str | None = None,
        chapter_metadata_path: str | None = None,
    ) -> str:
        """拼接分镜片段并复用字幕/章节，返回成片路径。"""
        if not clip_paths:
            raise ValueError("没有可合成的分镜片段")

        logger.info("开始合成: %d 个分镜片段 → %s", len(clip_paths), output_path)

        if not (srt_path or chapter_metadata_path):
            # 无字幕/章节：concat 结果即成片，需前置 moov 以便浏览器流式播放
            await ffmpeg.concat_clips(clip_paths, output_path, faststart=True)
            return output_path

        # 先拼接到临时文件，再复用软字幕/章节 metadata
        concat_out = f"{output_path}.concat.mp4"
        await ffmpeg.concat_clips(clip_paths, concat_out)
        try:
            await ffmpeg.mux_subtitle_and_chapters(
                concat_out,
                output_path,
                srt_path=srt_path,
                chapter_metadata_path=chapter_metadata_path,
            )
        finally:
            if os.path.exists(concat_out):
                os.remove(concat_out)

        logger.info("合成完成: %s", output_path)
        return output_path
