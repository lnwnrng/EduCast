"""资源服务 — 教学资源 CRUD 与版本管理。"""

import json
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ResourceNotFoundException
from app.models.resource import Resource


class ResourceService:
    """资源管理服务。"""

    @staticmethod
    async def create_resource(
        db: AsyncSession,
        project_id: UUID,
        resource_type: str,
        title: str,
        file_path: str,
        *,
        mime_type: str | None = None,
        version: int = 1,
        parent_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        watermark_applied: bool = False,
    ) -> Resource:
        """登记一条教学资源（自动读取文件大小）。

        resource_type: video / audio / image / subtitle / ir_snapshot / archive
        """
        file_size = 0
        try:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
        except OSError:
            pass

        resource = Resource(
            project_id=project_id,
            resource_type=resource_type,
            title=title,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            version=version,
            parent_id=parent_id,
            metadata_json=(
                json.dumps(metadata, ensure_ascii=False) if metadata else None
            ),
            watermark_applied=watermark_applied,
        )
        db.add(resource)
        await db.flush()
        await db.refresh(resource)
        return resource

    @staticmethod
    async def list_resources(
        db: AsyncSession,
        project_id: UUID | None = None,
        resource_type: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        user_project_ids: list[UUID] | None = None,
    ) -> tuple[list[Resource], int]:
        """分页查询资源列表。

        user_project_ids: 非 None 时限制只返回这些项目下的资源（普通用户权限控制）。
        """
        conditions = [Resource.deleted_at.is_(None)]
        if project_id:
            conditions.append(Resource.project_id == project_id)
        if resource_type:
            conditions.append(Resource.resource_type == resource_type)
        if search:
            conditions.append(Resource.title.ilike(f"%{search}%"))
        if user_project_ids is not None:
            conditions.append(Resource.project_id.in_(user_project_ids))

        count_stmt = select(func.count(Resource.id)).where(*conditions)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Resource)
            .where(*conditions)
            .order_by(Resource.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        resources = list(result.scalars().all())

        return resources, total

    @staticmethod
    async def get_resource(db: AsyncSession, resource_id: UUID) -> Resource:
        """获取资源详情。"""
        resource = await db.get(Resource, resource_id)
        if resource is None or resource.deleted_at is not None:
            raise ResourceNotFoundException(f"资源不存在: {resource_id}")
        return resource

    @staticmethod
    async def delete_resource(db: AsyncSession, resource_id: UUID) -> None:
        """软删除资源。"""
        resource = await ResourceService.get_resource(db, resource_id)
        resource.deleted_at = datetime.now(UTC)
        await db.flush()
