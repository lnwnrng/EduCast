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


# ── 视觉增强：转场 / 片头 / 片尾 ──────────────────────────


async def test_concat_with_transitions_builds_xfade_chain(
    capture_run, monkeypatch
) -> None:
    # probe_duration 返回固定时长，便于断言 offset 计算
    async def fake_probe(path: str) -> float:
        return 4.0

    monkeypatch.setattr(ffmpeg_mod, "probe_duration", fake_probe)

    await ffmpeg.concat_with_transitions(
        ["c0.mp4", "c1.mp4", "c2.mp4"],
        "out.mp4",
        transitions=["fade", "dissolve"],
        transition_duration=0.5,
    )
    args = capture_run["args"]
    fc = args[args.index("-filter_complex") + 1]
    # 两个转场 → 两条 xfade + 两条 acrossfade
    assert fc.count("xfade=") == 2
    assert "transition=fade" in fc and "transition=dissolve" in fc
    assert "acrossfade" in fc
    # 输出映射到 [vout]/[aout]
    assert "[vout]" in fc and "[aout]" in fc
    # 重编码为 H.264/AAC（xfade 必须重编码）
    assert "libx264" in args and "aac" in args


async def test_concat_with_transitions_all_cut_falls_back_to_concat(
    capture_run, monkeypatch
) -> None:
    """全 cut 转场退化为普通 concat（无损）。"""
    called = {"concat": False}

    async def fake_concat(clips, out, **kw) -> str:
        called["concat"] = True
        return out

    monkeypatch.setattr(ffmpeg_mod, "concat_clips", fake_concat)

    await ffmpeg.concat_with_transitions(
        ["c0.mp4", "c1.mp4"], "out.mp4", transitions=["cut"]
    )
    assert called["concat"] is True


async def test_concat_with_transitions_single_clip(capture_run) -> None:
    await ffmpeg.concat_with_transitions(["only.mp4"], "out.mp4")
    args = capture_run["args"]
    # 单片段直接 copy
    assert "only.mp4" in args and "-c" in args and "copy" in args


async def test_generate_intro_clip_draws_title(capture_run) -> None:
    await ffmpeg.generate_intro_clip("intro.mp4", title="线性代数导论", subject="数学")
    args = capture_run["args"]
    joined = " ".join(args)
    # color 背景输入 + drawtext 标题/学科/品牌
    assert "color=c=" in joined
    assert "drawtext" in joined and "线性代数导论" in joined
    assert "数学" in joined
    assert "课影 EduCast" in joined
    # libx264 编码 + 指定时长
    assert "libx264" in args and "-t" in args


async def test_generate_outro_clip_draws_title_and_summary(capture_run) -> None:
    await ffmpeg.generate_outro_clip(
        "outro.mp4", title="测试课程", summary_text="感谢观看"
    )
    args = capture_run["args"]
    joined = " ".join(args)
    assert "测试课程" in joined and "感谢观看" in joined
    assert "drawtext" in joined and "libx264" in args
