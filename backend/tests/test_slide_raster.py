"""slide_raster 工具测试 — PDF 栅格化（真实 fitz）与 soffice 探测。"""

from pathlib import Path

import fitz
from PIL import Image

from app.pipeline import slide_raster
from app.pipeline.slide_raster import find_soffice, pptx_to_pdf, rasterize_pdf


def _make_pdf(path: str, pages: int = 2) -> None:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(path)
    doc.close()


def test_rasterize_pdf_produces_png_per_page(tmp_path: Path) -> None:
    pdf = str(tmp_path / "doc.pdf")
    _make_pdf(pdf, pages=2)

    out = rasterize_pdf(pdf, str(tmp_path / "slides"), prefix="page", zoom=2.0)

    assert len(out) == 2
    for p in out:
        assert Path(p).exists()
        with Image.open(p) as im:
            assert im.width > 0 and im.height > 0


def test_find_soffice_returns_optional() -> None:
    res = find_soffice()
    assert res is None or isinstance(res, str)


def test_pptx_to_pdf_without_soffice_returns_none(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(slide_raster, "find_soffice", lambda: None)
    assert pptx_to_pdf(str(tmp_path / "x.pptx"), str(tmp_path)) is None
