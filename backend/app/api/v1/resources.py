"""资源管理 API。"""

import os
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.exceptions import ResourceNotFoundException
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.resource import ResourceResponse
from app.services.resource_service import ResourceService

router = APIRouter(prefix="/resources", tags=["资源管理"])


@router.get("/", response_model=PaginatedResponse[ResourceResponse])
async def list_resources(
    project_id: UUID | None = None,
    resource_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ResourceResponse]:
    """分页查询资源列表。"""
    resources, total = await ResourceService.list_resources(
        db, project_id, resource_type, page, page_size
    )
    return PaginatedResponse(
        items=[ResourceResponse.model_validate(r) for r in resources],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResourceResponse:
    """获取资源详情。"""
    resource = await ResourceService.get_resource(db, resource_id)
    return ResourceResponse.model_validate(resource)


@router.get("/{resource_id}/download")
async def download_resource(
    resource_id: UUID,
    download: bool = Query(False, description="true 强制下载，false 内联预览"),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """下载或在线预览资源文件（支持 Range，可供 <video> 播放）。"""
    resource = await ResourceService.get_resource(db, resource_id)
    if not os.path.exists(resource.file_path):
        raise ResourceNotFoundException(f"资源文件不存在: {resource_id}")
    return FileResponse(
        resource.file_path,
        media_type=resource.mime_type or "application/octet-stream",
        filename=os.path.basename(resource.file_path),
        content_disposition_type="attachment" if download else "inline",
    )


@router.delete("/{resource_id}", response_model=SuccessResponse)
async def delete_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """软删除资源。"""
    await ResourceService.delete_resource(db, resource_id)
    return SuccessResponse(message="资源已删除")
