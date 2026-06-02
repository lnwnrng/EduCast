"""课件页栅格化工具 — 把 PDF/PPTX 渲染为真实页图。

- PDF：用 PyMuPDF(fitz) 逐页栅格化（无新依赖）。
- PPTX：若本机装有 LibreOffice，则 soffice 转 PDF 后再栅格化；否则返回 None，
  由上层降级为 Pillow 文本合成。

这些是模块三课件「真实页图」的唯一外部渲染入口，便于单元测试 monkeypatch。
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# LibreOffice 常见安装路径（PATH 未命中时回退探测）
_SOFFICE_CANDIDATES = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice",
    "/usr/local/bin/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def rasterize_pdf(
    pdf_path: str,
    out_dir: str,
    *,
    prefix: str = "page",
    zoom: float = 2.0,
) -> list[str]:
    """把 PDF 逐页栅格化为 PNG，返回页图路径列表（按页序）。"""
    import fitz

    os.makedirs(out_dir, exist_ok=True)
    paths: list[str] = []
    matrix = fitz.Matrix(zoom, zoom)
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            out_path = os.path.join(out_dir, f"{prefix}_{i + 1}.png")
            pix.save(out_path)
            paths.append(out_path)
    logger.info("PDF 栅格化完成: %s → %d 页图", pdf_path, len(paths))
    return paths


def find_soffice() -> str | None:
    """探测 LibreOffice 的 soffice 可执行文件；未安装返回 None。"""
    found = shutil.which("soffice") or shutil.which("soffice.exe")
    if found:
        return found
    for cand in _SOFFICE_CANDIDATES:
        if os.path.exists(cand):
            return cand
    return None


def pptx_to_pdf(pptx_path: str, out_dir: str) -> str | None:
    """用 LibreOffice 把 PPTX 转为 PDF；无 soffice 或失败返回 None。"""
    soffice = find_soffice()
    if not soffice:
        logger.info("未检测到 LibreOffice，PPTX 跳过真实页图（降级文本合成）")
        return None

    os.makedirs(out_dir, exist_ok=True)
    try:
        subprocess.run(
            [
                soffice,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                out_dir,
                pptx_path,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("PPTX→PDF 转换失败: %s", exc)
        return None

    pdf_path = os.path.join(out_dir, f"{Path(pptx_path).stem}.pdf")
    return pdf_path if os.path.exists(pdf_path) else None
