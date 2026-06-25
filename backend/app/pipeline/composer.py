"""FFmpeg 视频合成器 — 把逐分镜片段拼接为最终教学视频。

职责很薄：调用 ``app.utils.ffmpeg`` 的原子操作完成「拼接 → 复用字幕/章节」。
逐分镜片段（静图+旁白）由 CompositionService 预先生成；字幕已烤进画面，这里
另把 SRT 作为软字幕、章节作为 metadata 复用进 MP4。

合成规格（来自 pipeline-orchestration SKILL）:
- 分辨率 1920×1080 / 编码 H.264+AAC / 帧率 30fps
- 字幕 SRT（软）+ 章节 FFmpeg metadata

视觉增强（可选，由 CompositionService 按配置启用）:
- ``transitions``：分镜间 xfade 转场（fade/dissolve/slide_left/slide_right/cut）
- ``intro_path`` / ``outro_path``：首尾插入动态片头/片尾片段
"""

import logging
import os

from app.ir.schema import TransitionType
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
        transitions: list[str] | None = None,
        intro_path: str | None = None,
        outro_path: str | None = None,
        transition_duration: float = 0.5,
    ) -> str:
        """拼接分镜片段并复用字幕/章节，返回成片路径。

        Args:
            clip_paths: 逐分镜片段路径（不含片头/片尾）。
            output_path: 成片输出路径。
            srt_path: SRT 字幕路径（软字幕复用）。
            chapter_metadata_path: FFmpeg metadata 章节路径。
            transitions: 分镜间转场类型列表（长度 = len(clip_paths)-1）。
                为空或全 'cut' 时退化为无损 concat。片头/片尾与首尾分镜间默认 fade。
            intro_path: 片头片段路径（插入到首镜之前）。
            outro_path: 片尾片段路径（追加到末镜之后）。
            transition_duration: 转场时长（秒）。
        """
        if not clip_paths:
            raise ValueError("没有可合成的分镜片段")

        # 组装实际参与拼接的片段列表 + 对应转场列表
        full_clips: list[str] = []
        full_trans: list[str] = []
        if intro_path:
            full_clips.append(intro_path)
            full_trans.append(TransitionType.FADE.value)
        full_clips.extend(clip_paths)
        if transitions:
            # clip 间的转场（clip_paths 内部）
            full_trans.extend(t for t in transitions[: max(len(clip_paths) - 1, 0)])
        if outro_path:
            full_clips.append(outro_path)
            full_trans.append(TransitionType.FADE.value)

        logger.info(
            "开始合成: %d 个片段（intro=%s, outro=%s, 转场=%s）→ %s",
            len(full_clips),
            bool(intro_path),
            bool(outro_path),
            bool(full_trans),
            output_path,
        )

        use_xfade = bool(full_trans) and not all(
            t == TransitionType.CUT.value for t in full_trans
        )

        if not (srt_path or chapter_metadata_path):
            # 无字幕/章节：直接输出成片
            await self._concat(
                full_clips,
                output_path,
                transitions=full_trans if use_xfade else None,
                transition_duration=transition_duration,
                faststart=True,
            )
            return output_path

        # 先拼接到临时文件，再复用软字幕/章节 metadata
        concat_out = f"{output_path}.concat.mp4"
        await self._concat(
            full_clips,
            concat_out,
            transitions=full_trans if use_xfade else None,
            transition_duration=transition_duration,
            faststart=False,
        )
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

    async def _concat(
        self,
        clips: list[str],
        output_path: str,
        *,
        transitions: list[str] | None = None,
        transition_duration: float = 0.5,
        faststart: bool = True,
    ) -> None:
        """按是否带转场选择拼接策略。"""
        if transitions:
            await ffmpeg.concat_with_transitions(
                clips,
                output_path,
                transitions,
                transition_duration=transition_duration,
                faststart=faststart,
            )
        else:
            await ffmpeg.concat_clips(clips, output_path, faststart=faststart)
