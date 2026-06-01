"""资源管理 API。"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.resource import ResourceResponse
from app.services.resource_service import ResourceService

router = APIRouter(prefix="/resources", tags=["资源管理"])


@router.get(
    "/", response_model=PaginatedResponse[ResourceResponse]
)
async def list_resources(
    project_id: Optional[UUID] = None,
    resource_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ResourceResponse]:
    """分页查询资源列表。"""
    resources, total = await ResourceService.list_resources(
        db, project_id, resource_type, page, page_size
    )
    return PaginatedResponse(
        items=[
            ResourceResponse.model_validate(r) for r in resources
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{resource_id}", response_model=ResourceResponse
)
async def get_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResourceResponse:
    """获取资源详情。"""
    resource = await ResourceService.get_resource(
        db, resource_id
    )
    return ResourceResponse.model_validate(resource)


@router.delete(
    "/{resource_id}", response_model=SuccessResponse
)
async def delete_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """软删除资源。"""
    await ResourceService.delete_resource(db, resource_id)
    return SuccessResponse(message="资源已删除")
