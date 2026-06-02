"""解析器真实页图测试 — PDF 解析后 slide_ref 指向真实栅格化页图。"""

import os
from pathlib import Path

import fitz

from app.pipeline.parser import DocumentParser


def _make_pdf(path: str, pages: int = 2) -> None:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Slide content page {i + 1}")
    doc.save(path)
    doc.close()


async def test_pdf_parse_sets_real_slide_ref(tmp_path: Path) -> None:
    pdf = str(tmp_path / "doc.pdf")
    _make_pdf(pdf, pages=2)

    parser = DocumentParser(storage_root=str(tmp_path / "storage"))
    ir = await parser.parse(pdf, ".pdf", project_id="proj1")

    scenes = [
        s
        for ch in ir.chapters
        for kp in ch.knowledge_points
        for s in kp.scenes
    ]
    assert scenes, "解析未产出任何分镜"

    real_refs = [
        s.visual_spec.slide_ref
        for s in scenes
        if s.visual_spec.slide_ref and os.path.exists(s.visual_spec.slide_ref)
    ]
    assert real_refs, "没有任何 slide_ref 指向真实文件"
    assert all("slides" in r for r in real_refs)
