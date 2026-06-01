"""资源服务 — 教学资源 CRUD 与版本管理。"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ResourceNotFoundException
from app.models.resource import Resource


class ResourceService:
    """资源管理服务。"""

    @staticmethod
    async def list_resources(
        db: AsyncSession,
        project_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Resource], int]:
        """分页查询资源列表。"""
        conditions = [Resource.deleted_at.is_(None)]
        if project_id:
            conditions.append(Resource.project_id == project_id)
        if resource_type:
            conditions.append(Resource.resource_type == resource_type)

        count_stmt = select(func.count(Resource.id)).where(
            *conditions
        )
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
    async def get_resource(
        db: AsyncSession, resource_id: UUID
    ) -> Resource:
        """获取资源详情。"""
        resource = await db.get(Resource, resource_id)
        if resource is None or resource.deleted_at is not None:
            raise ResourceNotFoundException(
                f"资源不存在: {resource_id}"
            )
        return resource

    @staticmethod
    async def delete_resource(
        db: AsyncSession, resource_id: UUID
    ) -> None:
        """软删除资源。"""
        resource = await ResourceService.get_resource(
            db, resource_id
        )
        resource.deleted_at = datetime.now(timezone.utc)
        await db.flush()
