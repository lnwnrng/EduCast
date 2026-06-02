"""解析服务 — 协调文档解析、IR 构建与存储。

职责:
  1. 调用 DocumentParser 解析文档
  2. 保存 IR 快照到文件系统
  3. 更新 Task 状态与 ir_snapshot_path
  4. 更新 Project 状态
"""

import json
import logging
import os
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import ParseException
from app.ir.schema import CourseIR
from app.ir.validator import validate_ir
from app.models.project import Project
from app.models.task import Task
from app.pipeline.parser import DocumentParser

logger = logging.getLogger(__name__)


class ParserService:
    """文档解析服务。"""

    def __init__(self) -> None:
        self._parser = DocumentParser(storage_root=settings.STORAGE_ROOT)

    async def parse_document(
        self,
        file_path: str,
        file_type: str,
        project_id: str,
        task_id: str,
        db: AsyncSession,
        advance_status: str = "reviewing",
        advance_progress: int = 40,
    ) -> CourseIR:
        """执行完整的文档解析流程。

        1. 更新 Task 状态 → parsing
        2. 调用解析器
        3. 保存 IR JSON
        4. 更新 Task.ir_snapshot_path
        5. 更新 Task 状态 → advance_status

        Args:
            file_path: 上传文件路径
            file_type: 文件扩展名
            project_id: 项目 ID
            task_id: 任务 ID
            db: 数据库会话
            advance_status: 解析成功后推进到的状态（默认 reviewing；链式接
                LLM 编排时传 "scripting"，避免前端在此处提前停轮询）。
            advance_progress: 解析成功后的进度百分比。

        Returns:
            生成的 CourseIR
        """
        try:
            # 1. 更新任务状态 → parsing
            await self._update_task(db, task_id, status="parsing", progress=10)

            # 2. 调用解析器
            logger.info(
                "开始解析: project=%s, file=%s",
                project_id,
                file_path,
            )
            ir = await self._parser.parse(file_path, file_type, project_id)

            # 3. 补充 IR 元信息
            ir.course_id = project_id

            # 4. 校验 IR
            errors = validate_ir(ir)
            if errors:
                logger.warning("IR 校验警告 (非致命): %s", errors)

            # 5. 保存 IR JSON
            ir_path = await self.save_ir(ir, project_id, version=1)

            # 6. 更新任务
            await self._update_task(
                db,
                task_id,
                status=advance_status,
                progress=advance_progress,
                ir_snapshot_path=ir_path,
            )

            # 7. 更新项目状态
            await self._update_project_status(db, project_id, status=advance_status)

            logger.info(
                "解析完成: project=%s, ir_path=%s",
                project_id,
                ir_path,
            )
            return ir

        except ParseException:
            await self._update_task(
                db,
                task_id,
                status="failed",
                progress=0,
                error_message="文档解析失败",
            )
            await self._update_project_status(db, project_id, status="failed")
            raise

        except Exception as exc:
            logger.error(
                "解析失败: project=%s, error=%s",
                project_id,
                exc,
                exc_info=True,
            )
            await self._update_task(
                db,
                task_id,
                status="failed",
                progress=0,
                error_message=str(exc),
            )
            await self._update_project_status(db, project_id, status="failed")
            raise ParseException(f"解析失败: {exc}") from exc

    async def save_ir(
        self,
        ir: CourseIR,
        project_id: str,
        version: int = 1,
    ) -> str:
        """保存 IR JSON 到文件系统。

        路径: storage/{project_id}/ir/v{version}.json

        Returns:
            IR 文件路径
        """
        ir_dir = os.path.join(settings.STORAGE_ROOT, project_id, "ir")
        os.makedirs(ir_dir, exist_ok=True)
        ir_path = os.path.join(ir_dir, f"v{version}.json")

        ir_json = ir.model_dump_json(indent=2)
        with open(ir_path, "w", encoding="utf-8") as f:
            f.write(ir_json)

        logger.info("IR 已保存: %s", ir_path)
        return ir_path

    async def load_ir(
        self,
        project_id: str,
        version: int | None = None,
    ) -> CourseIR | None:
        """从文件系统加载 IR JSON。

        Args:
            project_id: 项目 ID
            version: 版本号（None 则加载最新版本）

        Returns:
            CourseIR 或 None（文件不存在）
        """
        ir_dir = os.path.join(settings.STORAGE_ROOT, project_id, "ir")

        if version is not None:
            ir_path = os.path.join(ir_dir, f"v{version}.json")
        else:
            # 查找最新版本
            ir_path = self._find_latest_ir(ir_dir)

        if not ir_path or not os.path.exists(ir_path):
            return None

        with open(ir_path, encoding="utf-8") as f:
            data = json.load(f)

        return CourseIR.model_validate(data)

    def _find_latest_ir(self, ir_dir: str) -> str | None:
        """查找目录中最新版本的 IR 文件。"""
        if not os.path.exists(ir_dir):
            return None

        versions: list[tuple[int, str]] = []
        for fname in os.listdir(ir_dir):
            if fname.startswith("v") and fname.endswith(".json"):
                try:
                    v = int(fname[1:-5])  # v1.json → 1
                    versions.append((v, os.path.join(ir_dir, fname)))
                except ValueError:
                    continue

        if not versions:
            return None

        versions.sort(key=lambda x: x[0], reverse=True)
        return versions[0][1]

    async def _update_task(
        self,
        db: AsyncSession,
        task_id: str,
        status: str,
        progress: int,
        ir_snapshot_path: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """更新任务状态。"""
        try:
            pk = UUID(task_id)
        except (ValueError, AttributeError):
            return
        task = await db.get(Task, pk)
        if task:
            task.status = status
            task.progress = max(progress, 0)
            if ir_snapshot_path is not None:
                task.ir_snapshot_path = ir_snapshot_path
            if error_message is not None:
                task.error_message = error_message
            await db.commit()

    async def _update_project_status(
        self,
        db: AsyncSession,
        project_id: str,
        status: str,
    ) -> None:
        """更新项目状态。"""
        try:
            pk = UUID(project_id)
        except (ValueError, AttributeError):
            return
        project = await db.get(Project, pk)
        if project:
            project.status = status
            await db.commit()
