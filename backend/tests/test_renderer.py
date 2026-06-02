"""SlideRenderer（Pillow 课件渲染）测试 — 真实 Pillow，不依赖 FFmpeg。"""

from pathlib import Path

from PIL import Image

from app.pipeline import renderer as renderer_module
from app.pipeline.renderer import SlideRenderer


def _assert_valid_png(path: str, width: int = 1920, height: int = 1080) -> None:
    assert Path(path).exists()
    with Image.open(path) as im:
        assert im.size == (width, height)
        assert im.mode == "RGB"


def test_render_scene_produces_1080p_png(tmp_path: Path) -> None:
    out = str(tmp_path / "scene.png")
    result = SlideRenderer().render_scene(
        title="导数的定义",
        body_lines=["平均变化率", "瞬时变化率与极限", "导数定义式"],
        subtitle="我们先从平均变化率出发，理解导数的几何含义。",
        output_path=out,
        watermark="课影 EduCast",
        badge="讲解",
    )
    assert result == out
    _assert_valid_png(out)


def test_render_scene_wraps_long_text(tmp_path: Path) -> None:
    out = str(tmp_path / "long.png")
    long_subtitle = "导数" * 200  # 远超一行，触发换行与截断逻辑
    SlideRenderer().render_scene(
        title="非常长的标题" * 20,
        body_lines=["要点" * 100],
        subtitle=long_subtitle,
        output_path=out,
    )
    _assert_valid_png(out)


def test_render_scene_with_embedded_image(tmp_path: Path) -> None:
    # 造一张内嵌图
    img_path = tmp_path / "photo.png"
    Image.new("RGB", (400, 300), (200, 80, 80)).save(img_path)

    out = str(tmp_path / "with_img.png")
    SlideRenderer().render_scene(
        title="示意图",
        body_lines=["左侧文字", "右侧配图"],
        subtitle="配图说明",
        image_path=str(img_path),
        output_path=out,
    )
    _assert_valid_png(out)


def test_render_scene_missing_image_is_ignored(tmp_path: Path) -> None:
    out = str(tmp_path / "noimg.png")
    SlideRenderer().render_scene(
        title="标题",
        body_lines=["要点"],
        image_path=str(tmp_path / "does_not_exist.png"),
        output_path=out,
    )
    _assert_valid_png(out)


def test_render_cover(tmp_path: Path) -> None:
    out = str(tmp_path / "cover.png")
    SlideRenderer().render_cover(
        title="高等数学 · 导数",
        subject="高等数学",
        grade="大学一年级",
        output_path=out,
    )
    _assert_valid_png(out)


def test_render_formula_degrades_to_slide(tmp_path: Path) -> None:
    out = str(tmp_path / "formula.png")
    SlideRenderer().render_formula_animation(["f(x) = x^2", "f'(x) = 2x"], out)
    _assert_valid_png(out)


def test_font_fallback_when_no_cjk_font(tmp_path: Path, monkeypatch) -> None:
    """无任何 CJK 字体时回退 PIL 默认字体，渲染仍不崩、尺寸正确。"""
    monkeypatch.setattr(renderer_module, "_FONT_CANDIDATES", [])
    out = str(tmp_path / "fallback.png")
    r = SlideRenderer(font_path="")
    assert r._font_path is None
    r.render_scene(
        title="标题 title",
        body_lines=["bullet one", "要点二"],
        subtitle="caption 字幕",
        output_path=out,
    )
    _assert_valid_png(out)


def test_custom_resolution(tmp_path: Path) -> None:
    out = str(tmp_path / "720p.png")
    SlideRenderer(width=1280, height=720).render_scene(
        title="720p",
        body_lines=["a"],
        output_path=out,
    )
    _assert_valid_png(out, 1280, 720)
