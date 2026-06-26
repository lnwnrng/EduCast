"""任务与项目状态更新共享工具函数。

解决 ParserService / ScriptwriterService / CompositionService 中
_update_task / _update_project_status / _to_uuid 的重复代码问题。
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.task import Task

logger = logging.getLogger(__name__)


def to_uuid(value: str | UUID | None) -> UUID | None:
    """安全地将字符串/UUID 转换为 UUID 对象，失败返回 None。"""
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


async def update_task_status(
    db: AsyncSession,
    task_id: str | UUID,
    status: str,
    progress: int | None = None,
    *,
    step_detail: str | None = None,
    ir_snapshot_path: str | None = None,
    error_message: str | None = None,
    actual_cost: float | None = None,
) -> None:
    """更新任务状态（共享实现，替代各 Service 的私有 _update_task）。

    同时通过 WebSocket 广播进度给前端。

    Args:
        progress: 进度百分比；``None`` 表示保留现值（失败时不清零，进度条停在
            出错处）。
        step_detail: 当前子步骤的人类可读文案（如「编排第 3/12 个知识点」）。
    """
    pk = to_uuid(task_id)
    if pk is None:
        logger.warning("update_task_status: 无效的 task_id=%s", task_id)
        return
    task = await db.get(Task, pk)
    if task:
        task.status = status
        if progress is not None:
            task.progress = max(progress, 0)
        if step_detail is not None:
            task.step_detail = step_detail
        if ir_snapshot_path is not None:
            task.ir_snapshot_path = ir_snapshot_path
        if error_message is not None:
            task.error_message = error_message
        if actual_cost is not None:
            task.actual_cost = actual_cost
        await db.commit()

        # WebSocket 广播进度更新
        try:
            from app.api.v1.websocket import broadcast_progress

            await broadcast_progress(
                str(task.project_id),
                {
                    "task_id": str(task.id),
                    "project_id": str(task.project_id),
                    "status": status,
                    "progress": task.progress,
                    "step_detail": task.step_detail,
                    "error_message": error_message,
                },
            )
        except Exception:
            pass  # WebSocket 广播失败不影响正常流程


async def update_project_status(
    db: AsyncSession,
    project_id: str | UUID,
    status: str,
) -> None:
    """更新项目状态（共享实现，替代各 Service 的私有 _update_project_status）。"""
    pk = to_uuid(project_id)
    if pk is None:
        logger.warning("update_project_status: 无效的 project_id=%s", project_id)
        return
    project = await db.get(Project, pk)
    if project:
        project.status = status
        await db.commit()
