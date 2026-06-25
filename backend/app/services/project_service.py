"""项目服务 — 项目 CRUD 业务逻辑。"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import ResourceNotFoundException
from app.models.project import Project
from app.models.project_tag import project_tag
from app.models.tag import Tag
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    """项目 CRUD 服务。"""

    @staticmethod
    async def create_project(db: AsyncSession, data: ProjectCreate, user_id) -> Project:
        """创建新项目。"""
        project = Project(
            title=data.title,
            subject=data.subject,
            grade=data.grade,
            description=data.description,
            template=data.template,
            user_id=user_id,
            category_id=UUID(data.category_id) if data.category_id else None,
        )
        db.add(project)
        await db.flush()

        # Handle tags
        if data.tag_ids:
            tag_uuids = [UUID(tid) for tid in data.tag_ids]
            tag_result = await db.execute(select(Tag).where(Tag.id.in_(tag_uuids)))
            project.tags = list(tag_result.scalars().all())

        await db.flush()

        # 用 selectinload 重新查询，确保 category + tags 关系已加载
        result = await db.execute(
            select(Project)
            .where(Project.id == project.id)
            .options(selectinload(Project.category), selectinload(Project.tags))
        )
        return result.scalar_one()

    @staticmethod
    async def get_project(db: AsyncSession, project_id: UUID) -> Project:
        """获取项目详情。"""
        from sqlalchemy import select as sa_select

        result = await db.execute(
            sa_select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.category), selectinload(Project.tags))
        )
        project = result.scalar_one_or_none()
        if project is None or project.deleted_at is not None:
            raise ResourceNotFoundException(f"项目不存在: {project_id}")
        return project

    @staticmethod
    async def list_projects(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        user_id=None,
        is_admin: bool = False,
        category_id: str | None = None,
        tag_ids: list[str] | None = None,
    ) -> tuple[list[Project], int]:
        """分页查询项目列表。"""
        # ── 分类筛选（含子分类）──
        cat_uuids: list[UUID] | None = None
        if category_id:
            from app.models.category import CourseCategory

            cat_uuid = UUID(category_id)
            # 收集该分类及所有子分类的 ID
            all_cats = (await db.execute(select(CourseCategory))).scalars().all()
            cat_uuids = [cat_uuid]
            # BFS 收集子分类
            queue = [cat_uuid]
            while queue:
                parent = queue.pop(0)
                for c in all_cats:
                    if c.parent_id == parent and c.id not in cat_uuids:
                        cat_uuids.append(c.id)
                        queue.append(c.id)

        # ── 标签 UUID 转换 ──
        tag_uuids: list[UUID] | None = None
        if tag_ids:
            tag_uuids = [UUID(t) for t in tag_ids]

        # ── 总数查询 ──
        count_stmt = select(func.count(Project.id)).where(Project.deleted_at.is_(None))
        if not is_admin and user_id is not None:
            count_stmt = count_stmt.where(Project.user_id == user_id)
        if cat_uuids:
            count_stmt = count_stmt.where(Project.category_id.in_(cat_uuids))
        if tag_uuids:
            for tag_uuid in tag_uuids:
                count_stmt = count_stmt.where(
                    Project.id.in_(
                        select(project_tag.c.project_id).where(
                            project_tag.c.tag_id == tag_uuid
                        )
                    )
                )
        total = (await db.execute(count_stmt)).scalar() or 0

        # ── 分页数据查询 ──
        stmt = (
            select(Project)
            .where(Project.deleted_at.is_(None))
            .options(selectinload(Project.category), selectinload(Project.tags))
            .order_by(Project.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        if not is_admin and user_id is not None:
            stmt = stmt.where(Project.user_id == user_id)
        if cat_uuids:
            stmt = stmt.where(Project.category_id.in_(cat_uuids))
        if tag_uuids:
            for tag_uuid in tag_uuids:
                stmt = stmt.where(
                    Project.id.in_(
                        select(project_tag.c.project_id).where(
                            project_tag.c.tag_id == tag_uuid
                        )
                    )
                )
        result = await db.execute(stmt)
        projects = list(result.scalars().all())

        return projects, total

    @staticmethod
    async def update_project(
        db: AsyncSession,
        project_id: UUID,
        data: ProjectUpdate,
    ) -> Project:
        """更新项目。"""
        # 预加载 tags 和 category 关系，避免 async 模式下懒加载报 MissingGreenlet
        result = await db.execute(
            select(Project)
            .where(Project.id == project_id, Project.deleted_at.is_(None))
            .options(selectinload(Project.category), selectinload(Project.tags))
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise ResourceNotFoundException(f"项目不存在: {project_id}")

        # 修复 SQLite 可能返回字符串格式的 category_id
        if project.category_id and isinstance(project.category_id, str):
            project.category_id = UUID(project.category_id)

        update_data = data.model_dump(exclude_unset=True)
        tag_ids = update_data.pop("tag_ids", None)

        # 显式转换 category_id 为 UUID 对象
        if "category_id" in update_data and update_data["category_id"] is not None:
            update_data["category_id"] = UUID(str(update_data["category_id"]))

        for field, value in update_data.items():
            setattr(project, field, value)

        # Handle tags
        if tag_ids is not None:
            tag_uuids = [UUID(tid) for tid in tag_ids]
            tag_result = await db.execute(select(Tag).where(Tag.id.in_(tag_uuids)))
            project.tags = list(tag_result.scalars().all())

        await db.flush()

        # 重新查询，刷新 updated_at 同时保证关系已 eager load
        result = await db.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.category), selectinload(Project.tags))
        )
        return result.scalar_one()

    @staticmethod
    async def delete_project(db: AsyncSession, project_id: UUID) -> None:
        """软删除项目。"""
        project = await ProjectService.get_project(db, project_id)
        project.deleted_at = datetime.now(UTC)
        await db.flush()
