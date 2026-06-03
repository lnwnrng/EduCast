"""新增 FFmpeg 助手参数构建测试 — monkeypatch _run，断言命令而非跑真机。"""

import pytest

import app.utils.ffmpeg as ffmpeg_mod
from app.utils import ffmpeg

pytestmark = pytest.mark.asyncio


@pytest.fixture
def capture_run(monkeypatch):
    captured: dict = {}

    async def fake_run(args: list[str]) -> str:
        captured["args"] = args
        return ""

    monkeypatch.setattr(ffmpeg_mod, "_run", fake_run)
    return captured


async def test_video_audio_to_clip_loops_and_maps(capture_run) -> None:
    await ffmpeg.video_audio_to_clip(
        "in.mp4", "a.mp3", "out.mp4", width=1920, height=1080, fps=30, duration=6.0
    )
    args = capture_run["args"]
    assert "-stream_loop" in args  # 循环补足时长
    assert "in.mp4" in args and "a.mp3" in args
    assert "-t" in args and "6.0" in args
    # 显式映射视频与音频流
    assert "0:v" in args and "1:a" in args


async def test_video_audio_to_clip_silent_when_no_audio(capture_run) -> None:
    await ffmpeg.video_audio_to_clip("in.mp4", None, "out.mp4", duration=5.0)
    args = capture_run["args"]
    joined = " ".join(args)
    assert "anullsrc" in joined  # 无旁白 → 静音轨


async def test_kenburns_clip_uses_zoompan(capture_run) -> None:
    await ffmpeg.image_to_kenburns_clip(
        "img.png", "a.mp3", "out.mp4", fps=30, duration=5.0
    )
    args = capture_run["args"]
    joined = " ".join(args)
    assert "zoompan" in joined
    assert "-loop" in args and "img.png" in args
    assert "-t" in args and "5.0" in args


async def test_overlay_pip_positions_bottom_right(capture_run) -> None:
    await ffmpeg.overlay_pip_clip(
        "bg.png",
        "fg.png",
        "a.mp3",
        "out.mp4",
        position="bottom_right",
        size="small",
        duration=4.0,
    )
    args = capture_run["args"]
    fc = args[args.index("-filter_complex") + 1]
    assert "overlay=" in fc
    assert "W-w-" in fc  # 右下定位
    assert "sin(" in fc  # 静态前景的轻微浮动动感
    assert "[fg]" in fc and "[bg]" in fc


async def test_overlay_pip_full_screen(capture_run) -> None:
    await ffmpeg.overlay_pip_clip(
        "bg.png",
        "fg.mp4",
        "a.mp3",
        "out.mp4",
        position="full_screen",
        fg_is_video=True,
        duration=4.0,
    )
    args = capture_run["args"]
    fc = args[args.index("-filter_complex") + 1]
    assert "overlay=x=0:y=0" in fc  # 全屏铺满
    # 前景为视频 → 用 stream_loop 而非 loop 图片
    assert "-stream_loop" in args
