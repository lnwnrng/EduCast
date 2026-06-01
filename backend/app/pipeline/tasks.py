"""流水线任务编排 — 全流程异步任务管理。

任务状态机:
    PENDING → PARSING → SCRIPTING → REVIEWING → GENERATING → COMPOSING → COMPLETED / FAILED

P1 阶段使用 FastAPI BackgroundTasks，后续可迁移至 Celery。
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def run_full_pipeline(
    task_id: str,
    project_id: str,
    config: dict[str, Any],
    db: AsyncSession,
) -> None:
    """执行完整的视频生成流水线。

    编排流程:
    1. PARSING   — 文档解析 → IR 草稿
    2. SCRIPTING — LLM 脚本编排 → 完整 IR
    3. REVIEWING — 等待教师审核（人在环）
    4. GENERATING — 并行子任务（TTS + 渲染 + 数字人 + 生成式片段）
    5. COMPOSING — FFmpeg 合成
    6. COMPLETED — 入库

    TODO(P1): 完整实现各阶段逻辑
    """
    logger.info(
        "启动全流程流水线: task=%s, project=%s", task_id, project_id
    )

    try:
        # ── 1. PARSING ───────────────────────────────────
        await _update_task_status(db, task_id, "parsing", 10)
        logger.info("[%s] 阶段: 文档解析", task_id)
        # TODO: 调用 DocumentParser

        # ── 2. SCRIPTING ─────────────────────────────────
        await _update_task_status(db, task_id, "scripting", 30)
        logger.info("[%s] 阶段: 脚本编排", task_id)
        # TODO: 调用 ScriptWriter

        # ── 3. REVIEWING ─────────────────────────────────
        await _update_task_status(db, task_id, "reviewing", 40)
        logger.info("[%s] 阶段: 等待审核", task_id)
        # 人在环: 等待教师通过 API 审核通过

        # ── 4. GENERATING ────────────────────────────────
        await _update_task_status(db, task_id, "generating", 50)
        logger.info("[%s] 阶段: 并行生成", task_id)
        # TODO: 调度 TTS/渲染/数字人/生成式片段子任务

        # ── 5. COMPOSING ─────────────────────────────────
        await _update_task_status(db, task_id, "composing", 80)
        logger.info("[%s] 阶段: 视频合成", task_id)
        # TODO: 调用 VideoComposer

        # ── 6. COMPLETED ─────────────────────────────────
        await _update_task_status(db, task_id, "completed", 100)
        logger.info("[%s] 流水线完成", task_id)

    except Exception as exc:
        logger.error("[%s] 流水线失败: %s", task_id, exc)
        await _update_task_status(
            db, task_id, "failed", -1, str(exc)
        )


async def _update_task_status(
    db: AsyncSession,
    task_id: str,
    status: str,
    progress: int,
    error_message: str | None = None,
) -> None:
    """更新任务状态。"""
    from app.models.task import Task

    result = await db.get(Task, task_id)
    if result:
        result.status = status
        result.progress = max(progress, 0)
        if error_message:
            result.error_message = error_message
        await db.commit()
