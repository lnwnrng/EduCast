"""管理员 — 用户管理 & 审计日志。"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.middleware.auth import get_current_user_from_cookie
from app.models.audit_log import AuditLog
from app.models.project import Project
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.user import UserAdminResponse
from app.services.audit_service import AuditService

router = APIRouter(tags=["用户管理"])


@router.get("/users", response_model=PaginatedResponse[UserAdminResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str | None = Query(None),
    is_active: bool | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> PaginatedResponse[UserAdminResponse]:
    """用户列表（分页 + 筛选）。"""
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if search:
        query = query.where(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
            )
        )
    query = query.order_by(User.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    users = list(result.scalars().all())

    items = []
    for u in users:
        pc = await db.execute(
            select(func.count()).select_from(
                select(Project).where(Project.user_id == u.id).subquery()
            )
        )
        project_count = pc.scalar() or 0
        items.append(UserAdminResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role,
            is_active=u.is_active,
            last_login=u.last_login,
            created_at=u.created_at,
            updated_at=u.updated_at,
            project_count=project_count,
        ))

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.patch("/users/{user_id}/role", response_model=SuccessResponse)
async def change_user_role(
    user_id: str,
    role: str = Query(..., pattern="^(admin|user)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """修改用户角色。"""
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target_user.username == "admin":
        raise HTTPException(status_code=400, detail="不能修改默认管理员的角色")

    await db.execute(
        update(User).where(User.id == uuid.UUID(user_id)).values(role=role)
    )
    await AuditService.log(db, str(current_user.id), "role_change", "user", user_id, f"set role to {role}")
    return SuccessResponse(message=f"角色已更新为 {role}")


@router.patch("/users/{user_id}/toggle-active", response_model=SuccessResponse)
async def toggle_user_active(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """启用/禁用用户。"""
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="不能操作自己的账号")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="不能禁用默认管理员")

    user.is_active = not user.is_active
    status = "disabled" if not user.is_active else "enabled"
    await AuditService.log(db, str(current_user.id), "toggle_active", "user", user_id, status)
    return SuccessResponse(message=f"用户已{'禁用' if not user.is_active else '启用'}")


@router.delete("/users/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """删除用户。"""
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="不能删除自己的账号")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="不能删除默认管理员")

    await db.delete(user)
    await AuditService.log(db, str(current_user.id), "delete_user", "user", user_id)
    return SuccessResponse(message="用户已删除")


@router.get("/logs", response_model=PaginatedResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = Query(None),
    days: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> PaginatedResponse:
    """审计日志列表。"""
    items, total = await AuditService.list_logs(db, page, page_size, action, days)
    return PaginatedResponse(
        items=[{
            "id": str(log.id),
            "user_id": str(log.user_id),
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        } for log in items],
        total=total,
        page=page,
        page_size=page_size,
    )