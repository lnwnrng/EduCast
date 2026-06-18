"""视频模板市场 API — 模板浏览、创建、分享。"""

import json
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.exceptions import ResourceNotFoundException, ValidationException
from app.middleware.auth import get_current_user_from_cookie
from app.models.user import User
from app.models.video_template import VideoTemplate
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/templates", tags=["模板市场"])


@router.get("/", response_model=SuccessResponse)
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    category: str | None = Query(None, description="按分类筛选"),
    include_public: bool = Query(True, description="是否包含公开模板"),
) -> SuccessResponse:
    """浏览模板市场 — 返回系统模板 + 用户自建模板 + 公开模板。"""
    stmt = (
        select(VideoTemplate)
        .where(VideoTemplate.deleted_at.is_(None))
        .order_by(VideoTemplate.sort_order.asc(), VideoTemplate.usage_count.desc())
    )

    # 筛选: 系统模板 + 我的模板 + 公开模板
    from sqlalchemy import or_

    conditions = [
        VideoTemplate.is_system == True,  # noqa: E712
        VideoTemplate.creator_id == current_user.id,
    ]
    if include_public:
        conditions.append(VideoTemplate.is_public == True)  # noqa: E712

    stmt = stmt.where(or_(*conditions))

    if category:
        stmt = stmt.where(VideoTemplate.category == category)

    result = await db.execute(stmt)
    templates = result.scalars().all()

    return SuccessResponse(
        message="模板列表",
        data={
            "items": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "description": t.description,
                    "template_key": t.template_key,
                    "category": t.category,
                    "config_json": json.loads(t.config_json) if t.config_json else None,
                    "preview_image": t.preview_image,
                    "is_system": t.is_system,
                    "is_public": t.is_public,
                    "usage_count": t.usage_count,
                    "creator_id": str(t.creator_id) if t.creator_id else None,
                    "sort_order": t.sort_order,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in templates
            ],
            "total": len(templates),
        },
    )


@router.get("/categories", response_model=SuccessResponse)
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """获取所有模板分类。"""
    stmt = (
        select(VideoTemplate.category)
        .where(VideoTemplate.deleted_at.is_(None))
        .distinct()
    )
    result = await db.execute(stmt)
    categories = [row[0] for row in result.all()]

    return SuccessResponse(
        message="模板分类",
        data={"categories": categories},
    )


@router.post("/", response_model=SuccessResponse, status_code=201)
async def create_template(
    name: str,
    template_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    description: str | None = None,
    category: str = "general",
    config_json: str | None = None,
    preview_image: str | None = None,
    is_public: bool = False,
) -> SuccessResponse:
    """创建自定义模板。"""
    # 检查 template_key 唯一性
    existing = await db.execute(
        select(VideoTemplate).where(
            VideoTemplate.template_key == template_key,
            VideoTemplate.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise ValidationException(f"模板标识 '{template_key}' 已存在")

    template = VideoTemplate(
        name=name,
        description=description,
        template_key=template_key,
        category=category,
        config_json=config_json,
        preview_image=preview_image,
        is_system=False,
        is_public=is_public,
        creator_id=current_user.id,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)

    return SuccessResponse(
        message="模板创建成功",
        data={"id": str(template.id), "template_key": template.template_key},
    )


@router.put("/{template_id}", response_model=SuccessResponse)
async def update_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    name: str | None = None,
    description: str | None = None,
    category: str | None = None,
    config_json: str | None = None,
    preview_image: str | None = None,
    is_public: bool | None = None,
) -> SuccessResponse:
    """更新模板（只能更新自己创建的模板）。"""
    tid = uuid.UUID(template_id)
    template = await db.get(VideoTemplate, tid)
    if not template or template.deleted_at is not None:
        raise ResourceNotFoundException("模板不存在")
    if not template.is_system and template.creator_id != current_user.id and current_user.role != "admin":
        raise ValidationException("无权修改他人模板")

    if name is not None:
        template.name = name
    if description is not None:
        template.description = description
    if category is not None:
        template.category = category
    if config_json is not None:
        template.config_json = config_json
    if preview_image is not None:
        template.preview_image = preview_image
    if is_public is not None:
        template.is_public = is_public

    await db.flush()

    return SuccessResponse(message="模板更新成功")


@router.delete("/{template_id}", response_model=SuccessResponse)
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """软删除模板（系统模板不可删除）。"""
    from datetime import UTC, datetime

    tid = uuid.UUID(template_id)
    template = await db.get(VideoTemplate, tid)
    if not template or template.deleted_at is not None:
        raise ResourceNotFoundException("模板不存在")
    if template.is_system:
        raise ValidationException("系统内置模板不可删除")
    if template.creator_id != current_user.id and current_user.role != "admin":
        raise ValidationException("无权删除他人模板")

    template.deleted_at = datetime.now(UTC)

    return SuccessResponse(message="模板已删除")


@router.post("/{template_id}/use", response_model=SuccessResponse)
async def use_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """使用模板（增加使用次数统计）。"""
    tid = uuid.UUID(template_id)
    template = await db.get(VideoTemplate, tid)
    if not template or template.deleted_at is not None:
        raise ResourceNotFoundException("模板不存在")

    template.usage_count += 1
    await db.flush()

    return SuccessResponse(
        message="模板已使用",
        data={"template_key": template.template_key, "usage_count": template.usage_count},
    )
