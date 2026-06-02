"""任务服务 — 任务创建、状态管理、重试逻辑。"""

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import TaskNotFoundException
from app.models.task import SubTask, Task
from app.schemas.task import TaskCreate


class TaskService:
    """任务管理服务。"""

    @staticmethod
    async def create_task(
        db: AsyncSession,
        project_id: UUID,
        data: TaskCreate,
    ) -> Task:
        """创建新任务。"""
        task = Task(
            project_id=project_id,
            task_type=data.task_type,
            config_json=(json.dumps(data.config) if data.config else None),
        )
        db.add(task)
        await db.flush()
        await db.refresh(task)
        return task

    @staticmethod
    async def get_task(db: AsyncSession, task_id: UUID) -> Task:
        """获取任务详情。"""
        task = await db.get(Task, task_id)
        if task is None:
            raise TaskNotFoundException(f"任务不存在: {task_id}")
        return task

    @staticmethod
    async def get_subtasks(db: AsyncSession, task_id: UUID) -> list[SubTask]:
        """获取子任务列表。"""
        stmt = (
            select(SubTask)
            .where(SubTask.task_id == task_id)
            .order_by(SubTask.created_at)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_task_status(
        db: AsyncSession,
        task_id: UUID,
        status: str,
        progress: int = 0,
    ) -> Task:
        """更新任务状态。"""
        task = await TaskService.get_task(db, task_id)
        task.status = status
        task.progress = progress
        await db.flush()
        await db.refresh(task)
        return task

    @staticmethod
    async def retry_task(db: AsyncSession, task_id: UUID) -> Task:
        """重试失败的任务。"""
        task = await TaskService.get_task(db, task_id)
        if task.status != "failed":
            raise ValueError("只能重试失败的任务")
        task.status = "pending"
        task.progress = 0
        task.error_message = None
        await db.flush()
        await db.refresh(task)
        return task
