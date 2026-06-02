"""流水线任务编排 — 全流程异步任务管理。

任务状态机:
    PENDING → PARSING → SCRIPTING → REVIEWING
    → GENERATING → COMPOSING → COMPLETED / FAILED

P1 阶段使用 FastAPI BackgroundTasks，后续可迁移至 Celery。

说明：解析（模块一）与脚本编排（模块二）由上传流程在上游完成
（见 api/v1/upload.py），教师审核放行后进入生成与合成阶段。本函数把
「生成 → 合成 → 入库」整体委托给 CompositionService（其内部负责
generating → composing → completed 的状态推进与降级）。
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.composition_service import CompositionService

logger = logging.getLogger(__name__)


async def run_full_pipeline(
    task_id: str,
    project_id: str,
    config: dict[str, Any],
    db: AsyncSession,
) -> None:
    """从审核通过的 IR 执行「生成 → 合成 → 入库」。

    Args:
        task_id: 任务 ID。
        project_id: 项目 ID。
        config: 生成配置（预留：模板/分辨率/音色等）。
        db: 数据库会话。
    """
    logger.info(
        "启动生成合成流水线: task=%s, project=%s, config=%s",
        task_id,
        project_id,
        config,
    )
    await CompositionService().compose(
        project_id=project_id,
        task_id=task_id,
        db=db,
    )
