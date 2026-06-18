"""视频标注 API — 时间线批注 CRUD。"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.exceptions import ResourceNotFoundException, ValidationException
from app.middleware.auth import get_current_user_from_cookie
from app.models.annotation import Annotation
from app.models.project import Project
from app.models.user import User
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/annotations", tags=["视频标注"])


@router.get("/project/{project_id}", response_model=SuccessResponse)
async def list_annotations(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """获取项目的所有标注，按时间戳排序。"""
    pid = uuid.UUID(project_id)
    project = await db.get(Project, pid)
    if not project:
        raise ResourceNotFoundException("项目不存在")

    stmt = (
        select(Annotation)
        .where(
            Annotation.project_id == pid,
            Annotation.deleted_at.is_(None),
        )
        .order_by(Annotation.timestamp.asc(), Annotation.sort_order.asc())
    )
    result = await db.execute(stmt)
    annotations = result.scalars().all()

    return SuccessResponse(
        message="标注列表",
        data={
            "items": [
                {
                    "id": str(a.id),
                    "project_id": str(a.project_id),
                    "user_id": str(a.user_id),
                    "timestamp": a.timestamp,
                    "duration": a.duration,
                    "text": a.text,
                    "annotation_type": a.annotation_type,
                    "color": a.color,
                    "scene_id": a.scene_id,
                    "knowledge_point_id": a.knowledge_point_id,
                    "sort_order": a.sort_order,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in annotations
            ],
            "total": len(annotations),
        },
    )


@router.post("/", response_model=SuccessResponse, status_code=201)
async def create_annotation(
    project_id: str,
    timestamp: float,
    text: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    duration: float = 0.0,
    annotation_type: str = "note",
    color: str = "#1890ff",
    scene_id: str | None = None,
    knowledge_point_id: str | None = None,
) -> SuccessResponse:
    """创建时间线标注。"""
    pid = uuid.UUID(project_id)
    project = await db.get(Project, pid)
    if not project:
        raise ResourceNotFoundException("项目不存在")
    if not text.strip():
        raise ValidationException("标注内容不能为空")

    annotation = Annotation(
        project_id=pid,
        user_id=current_user.id,
        timestamp=timestamp,
        duration=duration,
        text=text.strip(),
        annotation_type=annotation_type,
        color=color,
        scene_id=scene_id,
        knowledge_point_id=knowledge_point_id,
    )
    db.add(annotation)
    await db.flush()
    await db.refresh(annotation)

    return SuccessResponse(
        message="标注创建成功",
        data={"id": str(annotation.id), "timestamp": annotation.timestamp},
    )


@router.put("/{annotation_id}", response_model=SuccessResponse)
async def update_annotation(
    annotation_id: str,
    text: str | None = None,
    timestamp: float | None = None,
    duration: float | None = None,
    color: str | None = None,
    annotation_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """更新标注内容。"""
    aid = uuid.UUID(annotation_id)
    annotation = await db.get(Annotation, aid)
    if not annotation or annotation.deleted_at is not None:
        raise ResourceNotFoundException("标注不存在")
    if annotation.user_id != current_user.id and current_user.role != "admin":
        raise ValidationException("无权修改他人标注")

    if text is not None:
        annotation.text = text.strip()
    if timestamp is not None:
        annotation.timestamp = timestamp
    if duration is not None:
        annotation.duration = duration
    if color is not None:
        annotation.color = color
    if annotation_type is not None:
        annotation.annotation_type = annotation_type

    await db.flush()

    return SuccessResponse(message="标注更新成功")


@router.delete("/{annotation_id}", response_model=SuccessResponse)
async def delete_annotation(
    annotation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """软删除标注。"""
    from datetime import UTC, datetime

    aid = uuid.UUID(annotation_id)
    annotation = await db.get(Annotation, aid)
    if not annotation or annotation.deleted_at is not None:
        raise ResourceNotFoundException("标注不存在")
    if annotation.user_id != current_user.id and current_user.role != "admin":
        raise ValidationException("无权删除他人标注")

    annotation.deleted_at = datetime.now(UTC)

    return SuccessResponse(message="标注已删除")
