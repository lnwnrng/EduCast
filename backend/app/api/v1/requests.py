"""分类/标签申请 API。"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.middleware.auth import get_current_user_from_cookie, require_admin
from app.models.category import CourseCategory
from app.models.category_tag_request import CategoryTagRequest
from app.models.tag import Tag
from app.models.user import User
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/requests", tags=["申请管理"])


# ── Pydantic Schema ────────────────────────────────────────
class RequestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="申请名称")
    type: str = Field(..., pattern="^(category|tag)$", description="申请类型: category 或 tag")
    reason: str = Field("", max_length=500, description="申请理由")


class RequestResponse(BaseModel):
    id: str
    name: str
    type: str
    reason: str
    status: str
    user_id: str
    username: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    created_at: str


# ── 普通用户提交申请 ─────────────────────────────────────
@router.post("/", response_model=SuccessResponse)
async def submit_request(
    data: RequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """提交分类/标签申请（所有登录用户）。"""
    # 检查是否已有同名同类型的 pending 申请
    existing = await db.execute(
        select(CategoryTagRequest).where(
            CategoryTagRequest.name == data.name,
            CategoryTagRequest.type == data.type,
            CategoryTagRequest.status == "pending",
            CategoryTagRequest.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "您已提交过相同名称和类型的申请，请等待审核")

    request = CategoryTagRequest(
        name=data.name,
        type=data.type,
        reason=data.reason,
        user_id=current_user.id,
    )
    db.add(request)
    await db.flush()
    return SuccessResponse(message="申请已提交，等待管理员审核")


# ── 查看申请列表 ─────────────────────────────────────────
@router.get("/", response_model=list[RequestResponse])
async def list_requests(
    status: str = Query(None, pattern="^(pending|approved|rejected)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> list[RequestResponse]:
    """查看申请列表。普通用户只能看自己的，管理员看全部。"""
    query = select(CategoryTagRequest).order_by(
        CategoryTagRequest.created_at.desc()
    )
    # 非管理员只看自己的
    if current_user.role != "admin":
        query = query.where(CategoryTagRequest.user_id == current_user.id)
    if status:
        query = query.where(CategoryTagRequest.status == status)

    result = await db.execute(query)
    requests = list(result.scalars().all())

    # 批量查询申请人用户名
    user_ids = {r.user_id for r in requests}
    username_map: dict[str, str] = {}
    if user_ids:
        user_result = await db.execute(
            select(User.id, User.username).where(User.id.in_(user_ids))
        )
        username_map = {str(row.id): row.username for row in user_result.all()}

    return [
        RequestResponse(
            id=str(r.id),
            name=r.name,
            type=r.type,
            reason=r.reason,
            status=r.status,
            user_id=str(r.user_id),
            username=username_map.get(str(r.user_id)),
            reviewed_by=str(r.reviewed_by) if r.reviewed_by else None,
            reviewed_at=r.reviewed_at.isoformat() if r.reviewed_at else None,
            created_at=r.created_at.isoformat(),
        )
        for r in requests
    ]


# ── 管理员：审核通过 ─────────────────────────────────────
@router.post("/{request_id}/approve", response_model=SuccessResponse, dependencies=[Depends(require_admin)])
async def approve_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """审核通过申请（仅管理员）。"""
    result = await db.execute(
        select(CategoryTagRequest).where(CategoryTagRequest.id == request_id)
    )
    request = result.scalar_one_or_none()
    if not request:
        raise HTTPException(404, "申请不存在")
    if request.status != "pending":
        raise HTTPException(400, "该申请已处理")

    # 创建对应的分类或标签
    if request.type == "category":
        # 检查是否已存在同名分类
        existing_cat = await db.execute(
            select(CourseCategory).where(CourseCategory.name == request.name)
        )
        if not existing_cat.scalar_one_or_none():
            db.add(CourseCategory(name=request.name))
    else:
        # 检查是否已存在同名标签
        existing_tag = await db.execute(
            select(Tag).where(Tag.name == request.name)
        )
        if not existing_tag.scalar_one_or_none():
            db.add(Tag(name=request.name))

    # 更新申请状态
    request.status = "approved"
    request.reviewed_by = current_user.id
    request.reviewed_at = datetime.now(timezone.utc)

    await db.flush()
    return SuccessResponse(message=f"已批准{'分类' if request.type == 'category' else '标签'}「{request.name}」")


# ── 管理员：拒绝申请 ─────────────────────────────────────
@router.post("/{request_id}/reject", response_model=SuccessResponse, dependencies=[Depends(require_admin)])
async def reject_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """拒绝申请（仅管理员）。"""
    result = await db.execute(
        select(CategoryTagRequest).where(CategoryTagRequest.id == request_id)
    )
    request = result.scalar_one_or_none()
    if not request:
        raise HTTPException(404, "申请不存在")
    if request.status != "pending":
        raise HTTPException(400, "该申请已处理")

    request.status = "rejected"
    request.reviewed_by = current_user.id
    request.reviewed_at = datetime.now(timezone.utc)

    await db.flush()
    return SuccessResponse(message="已拒绝该申请")
