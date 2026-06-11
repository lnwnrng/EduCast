"""标签管理 API。"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.middleware.auth import get_current_user_from_cookie, require_admin
from app.models.project_tag import project_tag
from app.models.tag import Tag
from app.models.user import User
from app.schemas.tag import TagCreate, TagResponse, TagUpdate


router = APIRouter(
    prefix="/tags",
    tags=["标签管理"],
)


@router.get("/", response_model=list[TagResponse])
async def list_tags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> list[TagResponse]:
    """标签列表（所有登录用户可读）。"""
    result = await db.execute(select(Tag).order_by(Tag.name))
    tags = list(result.scalars().all())
    items = []
    for t in tags:
        pc = await db.execute(
            select(func.count()).select_from(
                select(project_tag).where(project_tag.c.tag_id == t.id).subquery()
            )
        )
        items.append(TagResponse(
            id=str(t.id), name=t.name, color=t.color,
            project_count=pc.scalar() or 0, created_at=t.created_at,
        ))
    return items


@router.post("/", response_model=TagResponse, status_code=201, dependencies=[Depends(require_admin)])
async def create_tag(
    data: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> TagResponse:
    """创建标签（仅管理员）。"""
    tag = Tag(name=data.name, color=data.color)
    db.add(tag)
    await db.flush()
    await db.refresh(tag)
    return TagResponse(
        id=str(tag.id), name=tag.name, color=tag.color,
        project_count=0, created_at=tag.created_at,
    )


@router.put("/{tag_id}", response_model=TagResponse, dependencies=[Depends(require_admin)])
async def update_tag(
    tag_id: str,
    data: TagUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> TagResponse:
    """更新标签（仅管理员）。"""
    tag_uuid = uuid.UUID(tag_id)
    result = await db.execute(select(Tag).where(Tag.id == tag_uuid))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(404, "标签不存在")
    if data.name is not None:
        tag.name = data.name
    if data.color is not None:
        tag.color = data.color
    await db.flush()
    await db.refresh(tag)
    return TagResponse(
        id=str(tag.id), name=tag.name, color=tag.color,
        project_count=0, created_at=tag.created_at,
    )


@router.delete("/{tag_id}", dependencies=[Depends(require_admin)])
async def delete_tag(
    tag_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> dict:
    """删除标签（仅管理员）。"""
    tag_uuid = uuid.UUID(tag_id)
    result = await db.execute(select(Tag).where(Tag.id == tag_uuid))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(404, "标签不存在")
    await db.delete(tag)
    return {"message": "标签已删除"}