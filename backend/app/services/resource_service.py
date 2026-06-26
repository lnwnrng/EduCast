"""资源服务 — 教学资源 CRUD、文件夹层级与版本管理。"""

import json
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ResourceNotFoundException, ValidationException
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
        name: str | None = None,
    ) -> Resource:
        """登记一条教学资源（自动读取文件大小）。

        resource_type: video / audio / image / subtitle / ir_snapshot / archive / folder
        name 缺省时取 title，使网盘显示名与版本标题一致。
        """
        file_size = 0
        try:
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
        except OSError:
            pass

        resource = Resource(
            project_id=project_id,
            resource_type=resource_type,
            title=title,
            name=name if name is not None else title,
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
        is_folder: bool | None = None,
    ) -> tuple[list[Resource], int]:
        """分页查询资源列表。

        user_project_ids: 非 None 时限制只返回这些项目下的资源（普通用户权限控制）。
        is_folder: None=不过滤；True=仅文件夹；False=仅非文件夹（workspace 聚合用）。
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
        if is_folder is not None:
            conditions.append(Resource.is_folder == is_folder)

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
    async def list_children(
        db: AsyncSession,
        project_id: UUID,
        parent_id: UUID | None = None,
    ) -> list[Resource]:
        """单层列子项（parent_id=None 即项目虚拟根）。文件夹优先，按名称排序。"""
        stmt = (
            select(Resource)
            .where(
                Resource.project_id == project_id,
                Resource.deleted_at.is_(None),
                Resource.parent_id == parent_id,
            )
            .order_by(
                Resource.is_folder.desc(),
                func.coalesce(func.nullif(Resource.name, ""), Resource.title).asc(),
                Resource.created_at.desc(),
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_resource(db: AsyncSession, resource_id: UUID) -> Resource:
        """获取资源详情。"""
        resource = await db.get(Resource, resource_id)
        if resource is None or resource.deleted_at is not None:
            raise ResourceNotFoundException(f"资源不存在: {resource_id}")
        return resource

    @staticmethod
    async def create_folder(
        db: AsyncSession,
        project_id: UUID,
        name: str,
        parent_id: UUID | None = None,
    ) -> Resource:
        """建子文件夹。校验 parent_id 同项目且为文件夹或 None（项目根）。"""
        if parent_id is not None:
            parent = await db.get(Resource, parent_id)
            if parent is None or parent.deleted_at is not None:
                raise ResourceNotFoundException(f"父文件夹不存在: {parent_id}")
            if parent.project_id != project_id or not parent.is_folder:
                raise ValidationException("父文件夹无效")
        folder = Resource(
            project_id=project_id,
            resource_type="folder",
            title=name,
            name=name,
            file_path="",
            is_folder=True,
            parent_id=parent_id,
        )
        db.add(folder)
        await db.flush()
        await db.refresh(folder)
        return folder

    @staticmethod
    async def rename_resource(
        db: AsyncSession, resource_id: UUID, name: str
    ) -> Resource:
        """重命名资源/文件夹（改 name；文件夹同步 title 便于排序）。"""
        resource = await ResourceService.get_resource(db, resource_id)
        resource.name = name
        if resource.is_folder:
            resource.title = name
        await db.flush()
        await db.refresh(resource)
        return resource

    @staticmethod
    async def move_resource(
        db: AsyncSession,
        resource_id: UUID,
        parent_id: UUID | None = None,
    ) -> Resource:
        """移动资源/文件夹到指定父文件夹（parent_id=None 移回项目根）。

        校验：目标须同项目且为文件夹；不能移入自身或自己的子孙（环检测）。
        """
        resource = await ResourceService.get_resource(db, resource_id)
        if parent_id is not None:
            parent = await db.get(Resource, parent_id)
            if parent is None or parent.deleted_at is not None:
                raise ResourceNotFoundException(f"目标文件夹不存在: {parent_id}")
            if parent.project_id != resource.project_id or not parent.is_folder:
                raise ValidationException("目标文件夹无效")
            if parent_id == resource.id:
                raise ValidationException("不能将文件夹移入自身")
            if resource.is_folder:
                descendants = await ResourceService._collect_descendants(
                    db, resource.id
                )
                if parent_id in descendants:
                    raise ValidationException("不能将文件夹移入其子文件夹（会形成环）")
        resource.parent_id = parent_id
        await db.flush()
        await db.refresh(resource)
        return resource

    @staticmethod
    async def _collect_descendants(db: AsyncSession, folder_id: UUID) -> set[UUID]:
        """BFS 收集文件夹的所有子孙 ID（不含自身）。用于环检测与级联删除。"""
        descendants: set[UUID] = set()
        queue: list[UUID] = [folder_id]
        while queue:
            next_queue: list[UUID] = []
            for current in queue:
                result = await db.execute(
                    select(Resource.id).where(
                        Resource.parent_id == current,
                        Resource.deleted_at.is_(None),
                    )
                )
                for child_id in result.scalars().all():
                    if child_id not in descendants:
                        descendants.add(child_id)
                        next_queue.append(child_id)
            queue = next_queue
        return descendants

    @staticmethod
    async def delete_resource(db: AsyncSession, resource_id: UUID) -> None:
        """软删除资源；若为文件夹则级联软删所有子孙（物理文件不动）。"""
        resource = await ResourceService.get_resource(db, resource_id)
        now = datetime.now(UTC)
        if resource.is_folder:
            descendants = await ResourceService._collect_descendants(db, resource_id)
            for rid in [resource_id, *descendants]:
                r = await db.get(Resource, rid)
                if r and r.deleted_at is None:
                    r.deleted_at = now
        else:
            resource.deleted_at = now
        await db.flush()
