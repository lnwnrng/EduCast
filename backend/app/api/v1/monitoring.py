"""监控与成本 API（需求 5.5 监控面板 / 7.7 成本护栏）。

- GET /projects/{id}/cost-estimate — 审核前对最新 IR 做成本预估
- GET /projects/{id}/cost          — 项目成本/存储汇总
- GET /projects/{id}/workspace     — 项目工作台聚合（状态/版本/过期/成本）
- GET /monitoring/dashboard        — 全局监控面板聚合
"""

import json
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.exceptions import ResourceNotFoundException
from app.models.project import Project
from app.models.task import Task
from app.schemas.cost import CostEstimate, CostSummary, DashboardStats
from app.schemas.workspace import LatestTask, VideoVersion, WorkspaceResponse
from app.services import cost_service
from app.services.parser_service import ParserService
from app.services.resource_service import ResourceService

router = APIRouter(tags=["监控与成本"])

_parser_service = ParserService()


@router.get("/projects/{project_id}/cost-estimate", response_model=CostEstimate)
async def estimate_project_cost(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CostEstimate:
    """对项目最新 IR 做生成成本预估（审核前预览）。"""
    ir = await _parser_service.load_ir(str(project_id))
    if ir is None:
        raise ResourceNotFoundException(f"项目 {project_id} 尚未生成 IR")
    return cost_service.estimate_ir_cost(ir)


@router.get("/projects/{project_id}/cost", response_model=CostSummary)
async def get_project_cost(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CostSummary:
    """项目成本与存储用量汇总。"""
    return await cost_service.project_cost_summary(db, str(project_id))


@router.get("/projects/{project_id}/workspace", response_model=WorkspaceResponse)
async def get_workspace(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    """项目工作台聚合：状态 / IR 版本 / 成片版本 / 是否过期 / 成本 / 最新任务。"""
    project = await db.get(Project, project_id)
    if project is None:
        raise ResourceNotFoundException(f"项目 {project_id} 不存在")

    ir = await _parser_service.load_ir(str(project_id))
    latest_ir_version = ir.version if ir else None
    cost_estimate = cost_service.estimate_ir_cost(ir) if ir else None

    # 按生成版本聚合资源（video + 同版本的 vtt / archive）
    resources, _ = await ResourceService.list_resources(
        db, project_id=project_id, page=1, page_size=500
    )
    by_version: dict[int, dict] = {}
    for r in resources:
        slot = by_version.setdefault(r.version, {})
        if r.resource_type == "video":
            slot["video"] = r
        elif r.resource_type == "subtitle" and r.mime_type == "text/vtt":
            slot["vtt"] = r
        elif r.resource_type == "archive":
            slot["archive"] = r

    videos: list[VideoVersion] = []
    for v in sorted(by_version, reverse=True):
        slot = by_version[v]
        vid = slot.get("video")
        if vid is None:
            continue
        meta = json.loads(vid.metadata_json or "{}")
        videos.append(
            VideoVersion(
                version=v,
                ir_version=meta.get("ir_version"),
                resource_id=str(vid.id),
                subtitle_vtt_id=str(slot["vtt"].id) if slot.get("vtt") else None,
                archive_id=str(slot["archive"].id) if slot.get("archive") else None,
                created_at=vid.created_at.isoformat() if vid.created_at else None,
            )
        )

    has_video = bool(videos)
    latest_video_ir = videos[0].ir_version if has_video else None
    is_stale = (
        has_video
        and latest_ir_version is not None
        and latest_video_ir is not None
        and latest_ir_version > latest_video_ir
    )

    task_stmt = (
        select(Task)
        .where(Task.project_id == project_id)
        .order_by(Task.created_at.desc())
        .limit(1)
    )
    t = (await db.execute(task_stmt)).scalars().first()
    latest_task = (
        LatestTask(
            id=str(t.id),
            status=t.status,
            progress=t.progress,
            error_message=t.error_message,
        )
        if t
        else None
    )

    return WorkspaceResponse(
        project_id=str(project_id),
        title=project.title,
        status=project.status,
        subject=project.subject,
        grade=project.grade,
        has_ir=ir is not None,
        latest_ir_version=latest_ir_version,
        videos=videos,
        is_stale=is_stale,
        cost_estimate=cost_estimate,
        latest_task=latest_task,
    )


@router.get("/monitoring/dashboard", response_model=DashboardStats)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    """全局监控面板：任务状态分布、累计成本、存储用量、最近任务。"""
    return await cost_service.dashboard_stats(db)
