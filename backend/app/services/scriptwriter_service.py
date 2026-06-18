"""脚本编排服务 — 协调 LLM 编排、IR 版本保存与任务状态更新。

职责:
  1. 加载最新草稿 IR
  2. 调用 ScriptWriter 用 GLM-4.7-Flash 增强 IR
  3. 保存增强后的 IR 新版本
  4. 更新 Task / Project 状态（scripting → reviewing）

降级: LLM 失败或未配置 Key 时，ScriptWriter 内部已保证返回可用 IR，
本服务仍推进到 reviewing，不阻断流水线。
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.task import Task
from app.pipeline.scriptwriter import ScriptWriter
from app.providers.llm import get_llm_provider
from app.services.parser_service import ParserService
from app.utils.task_helpers import update_project_status, update_task_status

logger = logging.getLogger(__name__)


class ScriptwriterService:
    """LLM 脚本编排服务。"""

    def __init__(self) -> None:
        self._parser_service = ParserService()

    async def orchestrate(
        self,
        project_id: str,
        task_id: str,
        db: AsyncSession,
    ) -> None:
        """执行脚本编排流程。

        Args:
            project_id: 项目 ID。
            task_id: 任务 ID。
            db: 数据库会话。
        """
        # 1. 加载最新 IR
        current_ir = await self._parser_service.load_ir(project_id)
        if current_ir is None:
            logger.error("脚本编排找不到 IR: project=%s", project_id)
            await update_task_status(
                db,
                task_id,
                status="failed",
                progress=0,
                error_message="脚本编排失败：未找到 IR 草稿",
            )
            return

        try:
            # 2. 置编排中
            await update_task_status(db, task_id, status="scripting", progress=50)
            await update_project_status(db, project_id, "scripting")

            # 3. LLM 编排（进度 50 → 60）
            writer = ScriptWriter(get_llm_provider())

            async def _progress(done: int, total: int) -> None:
                pct = 50 + int(10 * done / total) if total else 60
                await update_task_status(db, task_id, status="scripting", progress=pct)

            enhanced = await writer.enhance_ir(current_ir, progress_cb=_progress)

            # 4. 保存新版本
            new_version = current_ir.version + 1
            enhanced.version = new_version
            ir_path = await self._parser_service.save_ir(
                enhanced, project_id, version=new_version
            )

            # 5. 推进到待审核
            await update_task_status(
                db,
                task_id,
                status="reviewing",
                progress=60,
                ir_snapshot_path=ir_path,
            )
            await update_project_status(db, project_id, "reviewing")

            logger.info(
                "脚本编排完成: project=%s, version=v%d",
                project_id,
                new_version,
            )

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "脚本编排失败: project=%s, error=%s",
                project_id,
                exc,
                exc_info=True,
            )
            await update_task_status(
                db,
                task_id,
                status="failed",
                progress=0,
                error_message=f"脚本编排失败: {exc}",
            )
            await update_project_status(db, project_id, "failed")

    # ── 状态更新（委托给共享工具函数）──────────────────────

    async def _update_task(
        self,
        db: AsyncSession,
        task_id: str,
        status: str,
        progress: int,
        ir_snapshot_path: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """更新任务状态（委托给共享 update_task_status）。"""
        await update_task_status(
            db, task_id, status, progress,
            ir_snapshot_path=ir_snapshot_path,
            error_message=error_message,
        )

    async def _update_project_status(
        self,
        db: AsyncSession,
        project_id: str,
        status: str,
    ) -> None:
        """更新项目状态（委托给共享 update_project_status）。"""
        await update_project_status(db, project_id, status)
