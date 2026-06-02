"""成本服务 — 生成前成本预估、配额护栏、成本/监控汇总（需求 7.7 / 5.5）。

价值核心之一：在按秒/次计费的生成式 API 介入前，先做单任务成本预估 + 项目级配额
拦截，避免超支。模块三为免费栈（估算 0），机制就位供模块 4/5 直接复用。

不改数据库 schema：项目花费 = Σ Task.actual_cost；存储用量 = Σ Resource.file_size。
"""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import CostLimitException
from app.ir.schema import CourseIR, SceneType
from app.models.resource import Resource
from app.models.task import Task
from app.providers.digital_human.placeholder import PlaceholderDigitalHumanProvider
from app.providers.video_gen.placeholder import PlaceholderVideoGenProvider
from app.schemas.cost import CostEstimate, CostSummary, DashboardStats

logger = logging.getLogger(__name__)

_DIGITAL_HUMAN = PlaceholderDigitalHumanProvider()
_VIDEO_GEN = PlaceholderVideoGenProvider()


def estimate_ir_cost(ir: CourseIR, config: dict | None = None) -> CostEstimate:
    """预估一份 IR 的生成成本（元）。

    - slide / formula_animation：本地渲染 + Edge-TTS，免费记 0。
    - digital_human：按旁白字数估口播时长 × 数字人费率。
    - generative_clip：按默认片段时长 × 生成式费率。
    """
    clip_seconds = float(
        (config or {}).get("clip_seconds", settings.GEN_CLIP_SECONDS)
    )
    breakdown: dict[str, float] = {}
    total = 0.0

    for chapter in ir.chapters:
        for kp in chapter.knowledge_points:
            for scene in kp.scenes:
                cost = 0.0
                if scene.scene_type == SceneType.DIGITAL_HUMAN:
                    chars = len((scene.narration_text or "").strip())
                    duration = chars / settings.TTS_CHARS_PER_SEC
                    cost = _DIGITAL_HUMAN.estimate_cost({"duration_sec": duration})
                elif scene.scene_type == SceneType.GENERATIVE_CLIP:
                    cost = _VIDEO_GEN.estimate_cost({"duration_sec": clip_seconds})

                if cost:
                    key = scene.scene_type.value
                    breakdown[key] = round(breakdown.get(key, 0.0) + cost, 4)
                    total += cost

    return CostEstimate(total=round(total, 4), breakdown=breakdown)


async def check_quota(
    db: AsyncSession, project_id: str, estimated: float
) -> None:
    """配额护栏：超单任务上限或项目累计上限则抛 CostLimitException（→ 429）。"""
    if estimated > settings.MAX_COST_PER_TASK:
        raise CostLimitException(
            f"预估成本 ¥{estimated:.2f} 超过单任务上限 "
            f"¥{settings.MAX_COST_PER_TASK:.2f}"
        )
    spent = await _project_spent(db, project_id)
    if spent + estimated > settings.MAX_COST_PER_PROJECT:
        raise CostLimitException(
            f"项目累计成本将达 ¥{spent + estimated:.2f}，超过项目上限 "
            f"¥{settings.MAX_COST_PER_PROJECT:.2f}"
        )


async def project_cost_summary(db: AsyncSession, project_id: str) -> CostSummary:
    """项目成本/存储汇总。"""
    pid = _to_uuid(project_id)
    status_counts, est_total, act_total, count = await _task_aggregates(
        db, project_id=pid
    )
    storage = await _storage_bytes(db, pid)
    return CostSummary(
        project_id=project_id,
        task_count=count,
        status_counts=status_counts,
        estimated_total=round(est_total, 4),
        actual_total=round(act_total, 4),
        storage_bytes=storage,
    )


async def dashboard_stats(db: AsyncSession) -> DashboardStats:
    """全局监控面板统计。"""
    status_counts, est_total, act_total, count = await _task_aggregates(db)
    storage = await _storage_bytes(db, None)

    recent_stmt = select(Task).order_by(Task.created_at.desc()).limit(10)
    recent = (await db.execute(recent_stmt)).scalars().all()
    recent_tasks = [
        {
            "id": str(t.id),
            "project_id": str(t.project_id),
            "status": t.status,
            "progress": t.progress,
            "estimated_cost": t.estimated_cost,
            "actual_cost": t.actual_cost,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in recent
    ]
    return DashboardStats(
        task_count=count,
        status_counts=status_counts,
        estimated_total=round(est_total, 4),
        actual_total=round(act_total, 4),
        storage_bytes=storage,
        recent_tasks=recent_tasks,
    )


# ── 内部聚合辅助 ─────────────────────────────────────────────


async def _task_aggregates(
    db: AsyncSession, project_id: UUID | None = None
) -> tuple[dict[str, int], float, float, int]:
    """返回 (状态分布, 估算合计, 实际合计, 任务总数)。"""
    conds = [Task.project_id == project_id] if project_id is not None else []

    status_stmt = select(Task.status, func.count()).group_by(Task.status)
    if conds:
        status_stmt = status_stmt.where(*conds)
    rows = (await db.execute(status_stmt)).all()
    status_counts = {status: int(n) for status, n in rows}
    count = sum(status_counts.values())

    sum_stmt = select(
        func.coalesce(func.sum(Task.estimated_cost), 0.0),
        func.coalesce(func.sum(Task.actual_cost), 0.0),
    )
    if conds:
        sum_stmt = sum_stmt.where(*conds)
    est_total, act_total = (await db.execute(sum_stmt)).one()
    return status_counts, float(est_total), float(act_total), count


async def _storage_bytes(db: AsyncSession, project_id: UUID | None) -> int:
    """项目（或全局）已落库资源的字节总量。"""
    conds = [Resource.deleted_at.is_(None)]
    if project_id is not None:
        conds.append(Resource.project_id == project_id)
    stmt = select(func.coalesce(func.sum(Resource.file_size), 0)).where(*conds)
    return int((await db.execute(stmt)).scalar() or 0)


async def _project_spent(db: AsyncSession, project_id: str) -> float:
    pid = _to_uuid(project_id)
    if pid is None:
        return 0.0
    stmt = select(func.coalesce(func.sum(Task.actual_cost), 0.0)).where(
        Task.project_id == pid
    )
    return float((await db.execute(stmt)).scalar() or 0.0)


def _to_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None
