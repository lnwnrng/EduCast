"""文档解析器 — 将异构教学文档转换为 IR 草稿。

支持: PPTX / PDF / DOCX / Markdown / 纯文本
"""

import logging
from pathlib import Path

from app.ir.schema import (
    ChapterIR,
    CourseIR,
    KnowledgePointIR,
    SceneIR,
    SceneType,
)

logger = logging.getLogger(__name__)

# 支持的文件类型
SUPPORTED_EXTENSIONS = {".pptx", ".pdf", ".docx", ".md", ".txt"}


class DocumentParser:
    """文档解析器 — 按文件类型分派到对应解析方法。"""

    async def parse(self, file_path: str, file_type: str) -> CourseIR:
        """解析文档，返回 IR 草稿。

        Args:
            file_path: 文件路径
            file_type: 文件扩展名（如 .pptx）

        Returns:
            课程脚本 IR 草稿
        """
        file_type = file_type.lower()
        logger.info("开始解析文档: %s (类型: %s)", file_path, file_type)

        parsers = {
            ".pptx": self._parse_pptx,
            ".pdf": self._parse_pdf,
            ".docx": self._parse_docx,
            ".md": self._parse_markdown,
            ".txt": self._parse_text,
        }

        parser = parsers.get(file_type)
        if parser is None:
            raise ValueError(f"不支持的文件类型: {file_type}")

        ir = await parser(file_path)
        logger.info(
            "文档解析完成: %d 章节",
            len(ir.chapters),
        )
        return ir

    async def _parse_pptx(self, file_path: str) -> CourseIR:
        """解析 PPTX 文件。

        TODO(P1): 使用 python-pptx 实现:
        - 逐页提取文本框、图片、表格、备注
        - 按标题层级切分章节与知识点
        - 识别公式区域（标注 LaTeX）
        - 图片关联到知识点
        """
        logger.info("PPTX 解析 (占位实现): %s", file_path)
        title = Path(file_path).stem
        return CourseIR(
            title=title,
            chapters=[
                ChapterIR(
                    title="第一章（自动解析）",
                    order=1,
                    knowledge_points=[
                        KnowledgePointIR(
                            title="知识点（待解析）",
                            scenes=[
                                SceneIR(
                                    order=1,
                                    scene_type=SceneType.SLIDE,
                                    narration_text="待 LLM 编排生成讲稿。",
                                    subtitle_text="待生成字幕。",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

    async def _parse_pdf(self, file_path: str) -> CourseIR:
        """解析 PDF 文件。

        TODO(P1): 使用 PyMuPDF/pdfplumber 实现。
        """
        logger.info("PDF 解析 (占位实现): %s", file_path)
        title = Path(file_path).stem
        return CourseIR(title=title)

    async def _parse_docx(self, file_path: str) -> CourseIR:
        """解析 DOCX 文件。

        TODO: 使用 mammoth 实现。
        """
        logger.info("DOCX 解析 (占位实现): %s", file_path)
        title = Path(file_path).stem
        return CourseIR(title=title)

    async def _parse_markdown(self, file_path: str) -> CourseIR:
        """解析 Markdown 文件。"""
        logger.info("Markdown 解析 (占位实现): %s", file_path)
        title = Path(file_path).stem
        return CourseIR(title=title)

    async def _parse_text(self, file_path: str) -> CourseIR:
        """解析纯文本文件。"""
        logger.info("文本解析 (占位实现): %s", file_path)
        title = Path(file_path).stem
        return CourseIR(title=title)
