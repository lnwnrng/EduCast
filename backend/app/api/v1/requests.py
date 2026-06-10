"""分类/标签申请 API。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.middleware.auth import get_current_user_from_cookie, require_admin
from app.models.category import CourseCategory
from app.models.category_tag_request import CategoryTagRequest
from app.models.tag import Tag
from app.models.user import User
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/requests", tags=["申请管理"])


# ── 申请 Schema ──────────────────────────────────────────
class RequestCreate:
    name: str
    type: str  # "category" or "tag"
    reason: str = ""


class RequestResponse:
    id: str
    name: str
    type: str
    reason: str
    status: str
    user_id: str
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    created_at: str


# ── 普通用户提交申请 ─────────────────────────────────────
@router.post("/", response_model=SuccessResponse)
async def submit_request(
    name: str = Query(..., min_length=1, max_length=100),
    type: str = Query(..., pattern="^(category|tag)$"),
    reason: str = Query("", max_length=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """提交分类/标签申请（所有登录用户）。"""
    request = CategoryTagRequest(
        name=name,
        type=type,
        reason=reason,
        user_id=current_user.id,
    )
    db.add(request)
    await db.flush()
    return SuccessResponse(message="申请已提交，等待管理员审核")


# ── 管理员：查看申请列表 ─────────────────────────────────
@router.get("/", dependencies=[Depends(require_admin)])
async def list_requests(
    status: str = Query(None, pattern="^(pending|approved|rejected)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> list[dict]:
    """查看申请列表（仅管理员）。"""
    query = select(CategoryTagRequest).order_by(
        CategoryTagRequest.created_at.desc()
    )
    if status:
        query = query.where(CategoryTagRequest.status == status)

    result = await db.execute(query)
    requests = list(result.scalars().all())

    return [
        {
            "id": str(r.id),
            "name": r.name,
            "type": r.type,
            "reason": r.reason,
            "status": r.status,
            "user_id": str(r.user_id),
            "reviewed_by": str(r.reviewed_by) if r.reviewed_by else None,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in requests
    ]


# ── 管理员：审核通过 ─────────────────────────────────────
@router.post("/{request_id}/approve", response_model=SuccessResponse, dependencies=[Depends(require_admin)])
async def approve_request(
    request_id: str,
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
        cat = CourseCategory(name=request.name)
        db.add(cat)
    else:
        tag = Tag(name=request.name)
        db.add(tag)

    # 更新申请状态
    request.status = "approved"
    request.reviewed_by = current_user.id
    request.reviewed_at = datetime.now(timezone.utc)

    await db.flush()
    return SuccessResponse(message=f"已批准{name}「{request.name}」")


# ── 管理员：拒绝申请 ─────────────────────────────────────
@router.post("/{request_id}/reject", response_model=SuccessResponse, dependencies=[Depends(require_admin)])
async def reject_request(
    request_id: str,
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
