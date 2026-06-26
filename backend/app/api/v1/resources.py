"""资源管理 API。"""

import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.exceptions import AuthorizationException, ResourceNotFoundException
from app.middleware.auth import get_current_user_from_cookie
from app.models.project import Project
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.resource import FolderCreate, ResourcePatch, ResourceResponse
from app.services.resource_service import ResourceService

router = APIRouter(prefix="/resources", tags=["资源管理"])


async def _get_user_project_ids(db: AsyncSession, user: User) -> list[UUID]:
    """获取当前用户的所有项目 ID。"""
    result = await db.execute(select(Project.id).where(Project.user_id == user.id))
    return [row[0] for row in result.all()]


async def _check_project_member(db: AsyncSession, project_id: UUID, user: User) -> None:
    """确保用户有权访问该项目（管理员跳过）。"""
    if user.role == "admin":
        return
    ids = await _get_user_project_ids(db, user)
    if project_id not in ids:
        raise AuthorizationException("无权访问该项目")


async def _check_resource_ownership(
    db: AsyncSession, resource_id: UUID, user: User
) -> None:
    """检查当前用户是否有权操作指定资源（管理员跳过）。"""
    if user.role == "admin":
        return
    resource = await ResourceService.get_resource(db, resource_id)
    project = await db.get(Project, resource.project_id)
    if not project or project.user_id != user.id:
        raise AuthorizationException("无权访问该资源")


@router.get("/", response_model=PaginatedResponse[ResourceResponse])
async def list_resources(
    project_id: UUID | None = None,
    resource_type: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> PaginatedResponse[ResourceResponse]:
    """分页查询资源列表（非管理员仅返回自己的资源）。"""
    user_project_ids: list[UUID] | None = None
    if current_user.role != "admin":
        user_project_ids = await _get_user_project_ids(db, current_user)
    resources, total = await ResourceService.list_resources(
        db,
        project_id,
        resource_type,
        search,
        page,
        page_size,
        user_project_ids=user_project_ids,
    )
    return PaginatedResponse(
        items=[ResourceResponse.model_validate(r) for r in resources],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/children", response_model=list[ResourceResponse])
async def list_children(
    project_id: UUID = Query(..., description="项目 ID"),
    parent_id: UUID | None = Query(None, description="父文件夹 ID，缺省=项目根"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> list[ResourceResponse]:
    """列出项目某文件夹下的子项（单层；网盘视图用）。"""
    await _check_project_member(db, project_id, current_user)
    items = await ResourceService.list_children(db, project_id, parent_id)
    return [ResourceResponse.model_validate(r) for r in items]


@router.post("/folders", response_model=ResourceResponse, status_code=201)
async def create_folder(
    data: FolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> ResourceResponse:
    """新建子文件夹（网盘）。"""
    await _check_project_member(db, data.project_id, current_user)
    folder = await ResourceService.create_folder(
        db, data.project_id, data.name, data.parent_id
    )
    return ResourceResponse.model_validate(folder)


@router.patch("/{resource_id}", response_model=ResourceResponse)
async def patch_resource(
    resource_id: UUID,
    data: ResourcePatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> ResourceResponse:
    """重命名 / 移动资源或文件夹。"""
    await _check_resource_ownership(db, resource_id, current_user)
    update = data.model_dump(exclude_unset=True)
    if "parent_id" in update:
        await ResourceService.move_resource(db, resource_id, update["parent_id"])
    if "name" in update:
        await ResourceService.rename_resource(db, resource_id, update["name"])
    resource = await ResourceService.get_resource(db, resource_id)
    return ResourceResponse.model_validate(resource)


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> ResourceResponse:
    """获取资源详情。"""
    await _check_resource_ownership(db, resource_id, current_user)
    resource = await ResourceService.get_resource(db, resource_id)
    return ResourceResponse.model_validate(resource)


@router.get("/{resource_id}/download")
async def download_resource(
    resource_id: UUID,
    download: bool = Query(False, description="true 强制下载，false 内联预览"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> FileResponse:
    """下载或在线预览资源文件（支持 Range，可供 <video> 播放）。"""
    await _check_resource_ownership(db, resource_id, current_user)
    resource = await ResourceService.get_resource(db, resource_id)
    if resource.is_folder:
        raise HTTPException(400, "文件夹不支持下载")
    if not os.path.exists(resource.file_path):
        raise ResourceNotFoundException(f"资源文件不存在: {resource_id}")
    # 防止路径遍历攻击：确保文件在 STORAGE_ROOT 内
    if not os.path.abspath(resource.file_path).startswith(
        os.path.abspath(settings.STORAGE_ROOT)
    ):
        raise ResourceNotFoundException("资源文件不存在")
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
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """删除资源；若为文件夹则级联软删其下所有内容。"""
    await _check_resource_ownership(db, resource_id, current_user)
    await ResourceService.delete_resource(db, resource_id)
    return SuccessResponse(message="资源已删除")
