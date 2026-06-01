"""解析服务集成测试。

覆盖:
  - parse_document 完整流程
  - IR 保存与加载
  - 版本管理
  - 错误状态更新
"""

import io
import json
import os
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.ir.schema import ChapterIR, CourseIR, KnowledgePointIR, SceneIR, SceneType
from app.models.project import Project
from app.models.task import Task
from app.services.parser_service import ParserService


# ── fixtures ─────────────────────────────────────────────


@pytest.fixture
def parser_service() -> ParserService:
    """创建解析服务实例。"""
    return ParserService()


@pytest.fixture
def sample_md_file(tmp_path: Path) -> str:
    """创建一个测试 Markdown 文件。"""
    content = """# 线性代数

## 矩阵

矩阵是按照长方阵列排列的复数或实数集合。

## 行列式

行列式是矩阵的一个标量属性。
"""
    file_path = str(tmp_path / "linear_algebra.md")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path


@pytest.fixture
def sample_txt_file(tmp_path: Path) -> str:
    """创建一个测试纯文本文件。"""
    content = "测试内容\n\n这是第二段。"
    file_path = str(tmp_path / "test.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path


# ── IR 保存与加载测试 ────────────────────────────────────


class TestIRPersistence:
    """IR 持久化测试。"""

    @pytest.mark.asyncio
    async def test_save_and_load_ir(
        self, parser_service: ParserService, tmp_path: Path
    ) -> None:
        """保存和加载 IR。"""
        # 修改 storage root 为临时目录
        from app.config import settings
        original_root = settings.STORAGE_ROOT
        settings.STORAGE_ROOT = str(tmp_path / "storage")

        try:
            # 创建一个简单 IR
            ir = CourseIR(
                title="测试课程",
                chapters=[
                    ChapterIR(
                        title="第一章",
                        order=1,
                        knowledge_points=[
                            KnowledgePointIR(
                                title="知识点1",
                                scenes=[
                                    SceneIR(
                                        order=1,
                                        scene_type=SceneType.SLIDE,
                                        narration_text="旁白",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            )

            # 保存
            project_id = "test-project-123"
            ir_path = await parser_service.save_ir(
                ir, project_id, version=1
            )
            assert os.path.exists(ir_path)
            assert "v1.json" in ir_path

            # 验证文件内容
            with open(ir_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["title"] == "测试课程"

            # 加载
            loaded_ir = await parser_service.load_ir(project_id, version=1)
            assert loaded_ir is not None
            assert loaded_ir.title == "测试课程"
            assert len(loaded_ir.chapters) == 1

        finally:
            settings.STORAGE_ROOT = original_root

    @pytest.mark.asyncio
    async def test_load_latest_version(
        self, parser_service: ParserService, tmp_path: Path
    ) -> None:
        """加载最新版本的 IR。"""
        from app.config import settings
        original_root = settings.STORAGE_ROOT
        settings.STORAGE_ROOT = str(tmp_path / "storage")

        try:
            project_id = "test-version"

            # 保存多个版本
            ir_v1 = CourseIR(title="版本1")
            ir_v2 = CourseIR(title="版本2")
            ir_v3 = CourseIR(title="版本3")

            await parser_service.save_ir(ir_v1, project_id, version=1)
            await parser_service.save_ir(ir_v2, project_id, version=2)
            await parser_service.save_ir(ir_v3, project_id, version=3)

            # 加载最新版本（不指定版本号）
            latest = await parser_service.load_ir(project_id)
            assert latest is not None
            assert latest.title == "版本3"

            # 加载指定版本
            v1 = await parser_service.load_ir(project_id, version=1)
            assert v1 is not None
            assert v1.title == "版本1"

        finally:
            settings.STORAGE_ROOT = original_root

    @pytest.mark.asyncio
    async def test_load_nonexistent_ir(
        self, parser_service: ParserService, tmp_path: Path
    ) -> None:
        """加载不存在的 IR 返回 None。"""
        from app.config import settings
        original_root = settings.STORAGE_ROOT
        settings.STORAGE_ROOT = str(tmp_path / "storage")

        try:
            result = await parser_service.load_ir("nonexistent")
            assert result is None
        finally:
            settings.STORAGE_ROOT = original_root

    @pytest.mark.asyncio
    async def test_ir_json_format(
        self, parser_service: ParserService, tmp_path: Path
    ) -> None:
        """保存的 IR JSON 应格式化（indent=2）。"""
        from app.config import settings
        original_root = settings.STORAGE_ROOT
        settings.STORAGE_ROOT = str(tmp_path / "storage")

        try:
            ir = CourseIR(title="格式化测试")
            project_id = "format-test"
            ir_path = await parser_service.save_ir(
                ir, project_id, version=1
            )

            with open(ir_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 应该是格式化的 JSON（有换行和缩进）
            assert "\n" in content
            assert "  " in content

        finally:
            settings.STORAGE_ROOT = original_root


# ── IR 内容完整性测试 ────────────────────────────────────


class TestIRContentIntegrity:
    """IR 内容完整性测试。"""

    @pytest.mark.asyncio
    async def test_ir_roundtrip_preserves_all_fields(
        self, parser_service: ParserService, tmp_path: Path
    ) -> None:
        """IR 序列化 → 反序列化保留所有字段。"""
        from app.config import settings
        from app.ir.schema import VisualSpec

        original_root = settings.STORAGE_ROOT
        settings.STORAGE_ROOT = str(tmp_path / "storage")

        try:
            ir = CourseIR(
                title="完整性测试",
                subject="math",
                grade="大一",
                chapters=[
                    ChapterIR(
                        title="章节",
                        order=1,
                        source_pages=[1, 2],
                        knowledge_points=[
                            KnowledgePointIR(
                                title="KP",
                                key_points=["要点1", "要点2"],
                                tags=["标签"],
                                scenes=[
                                    SceneIR(
                                        order=1,
                                        scene_type=SceneType.SLIDE,
                                        narration_text="旁白",
                                        subtitle_text="字幕",
                                        visual_spec=VisualSpec(
                                            slide_ref="s1.png",
                                        ),
                                        source_page=1,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            )

            project_id = "integrity-test"
            await parser_service.save_ir(ir, project_id, version=1)

            loaded = await parser_service.load_ir(project_id, version=1)
            assert loaded is not None
            assert loaded.title == ir.title
            assert loaded.subject == ir.subject
            assert loaded.grade == ir.grade
            assert len(loaded.chapters) == 1

            ch = loaded.chapters[0]
            assert ch.source_pages == [1, 2]

            kp = ch.knowledge_points[0]
            assert kp.key_points == ["要点1", "要点2"]
            assert kp.tags == ["标签"]

            scene = kp.scenes[0]
            assert scene.narration_text == "旁白"
            assert scene.visual_spec.slide_ref == "s1.png"
            assert scene.source_page == 1

        finally:
            settings.STORAGE_ROOT = original_root
