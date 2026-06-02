"""项目管理 API。"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["项目管理"])


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """创建新项目。"""
    project = await ProjectService.create_project(db, data)
    return ProjectResponse.model_validate(project)


@router.get("/", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProjectResponse]:
    """分页查询项目列表。"""
    projects, total = await ProjectService.list_projects(db, page, page_size)
    return PaginatedResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """获取项目详情。"""
    project = await ProjectService.get_project(db, project_id)
    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """更新项目信息。"""
    project = await ProjectService.update_project(db, project_id, data)
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", response_model=SuccessResponse)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """软删除项目。"""
    await ProjectService.delete_project(db, project_id)
    return SuccessResponse(message="项目已删除")
