"""真实 FFmpeg 集成测试 — 仅在本机装有 ffmpeg 时运行。

验证 utils.ffmpeg 的合成助手与 VideoComposer 能产出可被 ffprobe 识别的 MP4。
未安装 ffmpeg 时整文件跳过（CI/无 ffmpeg 开发机不受影响）。
"""

import shutil
from pathlib import Path

import pytest

from app.pipeline.composer import VideoComposer
from app.pipeline.renderer import SlideRenderer
from app.pipeline.subtitles import build_chapter_metadata, build_srt
from app.utils import ffmpeg

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="本机未安装 ffmpeg/ffprobe",
)


async def test_clip_concat_and_probe(tmp_path: Path) -> None:
    renderer = SlideRenderer(width=640, height=360)
    clips = []
    for i in range(2):
        img = str(tmp_path / f"s{i}.png")
        renderer.render_scene(
            title=f"第 {i + 1} 镜",
            body_lines=["要点一", "要点二"],
            subtitle=f"这是第 {i + 1} 个分镜的字幕",
            output_path=img,
        )
        clip = str(tmp_path / f"clip{i}.mp4")
        await ffmpeg.image_audio_to_clip(
            img, None, clip, width=640, height=360, fps=24, duration=1.0
        )
        assert Path(clip).exists()
        assert await ffmpeg.probe_duration(clip) > 0.5
        clips.append(clip)

    # 字幕 + 章节
    srt = str(tmp_path / "subs.srt")
    chapters = str(tmp_path / "chapters.txt")
    Path(srt).write_text(
        build_srt([(0.0, 1.0, "第一镜"), (1.0, 2.0, "第二镜")]), encoding="utf-8"
    )
    Path(chapters).write_text(
        build_chapter_metadata([(0.0, 2.0, "第一章")]), encoding="utf-8"
    )

    out = str(tmp_path / "final.mp4")
    await VideoComposer().compose(
        clips, out, srt_path=srt, chapter_metadata_path=chapters
    )

    assert Path(out).exists()
    total = await ffmpeg.probe_duration(out)
    assert total > 1.5  # 两段各约 1s
