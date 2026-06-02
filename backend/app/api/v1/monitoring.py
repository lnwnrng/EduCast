"""监控与成本 API（需求 5.5 监控面板 / 7.7 成本护栏）。

- GET /projects/{id}/cost-estimate — 审核前对最新 IR 做成本预估
- GET /projects/{id}/cost          — 项目成本/存储汇总
- GET /monitoring/dashboard        — 全局监控面板聚合
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.exceptions import ResourceNotFoundException
from app.schemas.cost import CostEstimate, CostSummary, DashboardStats
from app.services import cost_service
from app.services.parser_service import ParserService

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


@router.get("/monitoring/dashboard", response_model=DashboardStats)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    """全局监控面板：任务状态分布、累计成本、存储用量、最近任务。"""
    return await cost_service.dashboard_stats(db)
