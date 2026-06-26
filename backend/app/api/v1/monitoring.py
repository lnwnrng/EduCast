"""监控与成本 API（需求 5.5 监控面板 / 7.7 成本护栏）。

- GET /projects/{id}/cost-estimate — 审核前对最新 IR 做成本预估
- GET /projects/{id}/cost          — 项目成本/存储汇总
- GET /projects/{id}/workspace     — 项目工作台聚合（状态/版本/过期/成本）
- GET /monitoring/dashboard        — 全局监控面板聚合
"""

import json
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.exceptions import ResourceNotFoundException
from app.middleware.auth import get_current_user_from_cookie
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.cost import CostEstimate, CostSummary
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
    current_user: User = Depends(get_current_user_from_cookie),
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
    current_user: User = Depends(get_current_user_from_cookie),
) -> CostSummary:
    """项目成本与存储用量汇总。"""
    return await cost_service.project_cost_summary(db, str(project_id))


@router.get("/projects/{project_id}/workspace", response_model=WorkspaceResponse)
async def get_workspace(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> WorkspaceResponse:
    """项目工作台聚合：状态 / IR 版本 / 成片版本 / 是否过期 / 成本 / 最新任务。"""
    project = await db.get(Project, project_id)
    if project is None:
        raise ResourceNotFoundException(f"项目 {project_id} 不存在")

    ir = await _parser_service.load_ir(str(project_id))
    latest_ir_version = ir.version if ir else None
    cost_estimate = cost_service.estimate_ir_cost(ir) if ir else None

    # 按生成版本聚合资源（video + 同版本的 vtt / archive；排除文件夹行）
    resources, _ = await ResourceService.list_resources(
        db, project_id=project_id, page=1, page_size=500, is_folder=False
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
            step_detail=t.step_detail,
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


@router.get("/monitoring/dashboard", response_model=dict)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> dict:
    """全局监控面板聚合。"""
    from app.services import cost_service

    base = await cost_service.dashboard_stats(db)
    result = base.model_dump()

    # Admin-only extended stats
    if current_user.role == "admin":
        from app.models.user import User as UserModel

        user_count = (await db.execute(select(func.count(UserModel.id)))).scalar() or 0
        today_reg = (
            await db.execute(
                select(func.count(UserModel.id)).where(
                    func.date(UserModel.created_at) == func.current_date()
                )
            )
        ).scalar() or 0
        project_count = (
            await db.execute(
                select(func.count(Project.id)).where(Project.deleted_at.is_(None))
            )
        ).scalar() or 0
        storage_bytes = result.get("storage_bytes", 0)

        result["admin_stats"] = {
            "user_count": user_count,
            "today_registrations": today_reg,
            "project_count": project_count,
            "storage_bytes": storage_bytes,
        }

    return result


@router.get("/monitoring/health")
async def system_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> list[dict]:
    """系统健康检查（仅管理员）。"""
    from app.middleware.auth import require_admin

    await require_admin(current_user)
    from app.services.health_service import HealthService

    return await HealthService.run_all(db)
