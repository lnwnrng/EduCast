"""FormulaRenderer 测试 — 图片显影兜底路径（monkeypatch ffmpeg，真实 matplotlib）。"""

from pathlib import Path

import pytest

import app.utils.ffmpeg as ffmpeg_mod
from app.pipeline.formula import FormulaRenderer


@pytest.fixture
def fake_ffmpeg(monkeypatch):
    async def fake_clip(image, audio, out, **kw) -> str:
        Path(out).write_bytes(b"clip")
        return out

    async def fake_concat(clips, out, **kw) -> str:
        Path(out).write_bytes(b"video")
        return out

    monkeypatch.setattr(ffmpeg_mod, "image_audio_to_clip", fake_clip)
    monkeypatch.setattr(ffmpeg_mod, "concat_clips", fake_concat)


async def test_empty_steps_raises(tmp_path) -> None:
    with pytest.raises(ValueError):
        await FormulaRenderer().render([], str(tmp_path / "o.mp4"))


async def test_image_engine_produces_mp4(fake_ffmpeg, tmp_path) -> None:
    out = tmp_path / "f.mp4"
    await FormulaRenderer(engine="image").render(
        ["f(x) = x^2", "f'(x) = 2x"], str(out), duration=4.0
    )
    assert out.exists()


async def test_invalid_mathtext_degrades_to_plain(fake_ffmpeg, tmp_path) -> None:
    """非法 mathtext 步骤自动退化为纯文本，不抛异常仍出片。"""
    out = tmp_path / "f.mp4"
    await FormulaRenderer(engine="image").render(
        [r"\unknownmacro{", "普通文字步骤"], str(out)
    )
    assert out.exists()


def test_manim_not_available_in_this_env() -> None:
    # 本环境未安装 manim → auto 走图片显影，不会因缺依赖报错
    assert FormulaRenderer._manim_available() is False
