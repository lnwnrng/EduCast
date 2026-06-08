"""项目服务 — 项目 CRUD 业务逻辑。"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ResourceNotFoundException
from app.models.project import Project
from app.models.project_tag import project_tag
from app.models.tag import Tag
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    """项目 CRUD 服务。"""

    @staticmethod
    async def create_project(
        db: AsyncSession, data: ProjectCreate, user_id
    ) -> Project:
        """创建新项目。"""
        project = Project(
            title=data.title,
            subject=data.subject,
            grade=data.grade,
            description=data.description,
            template=data.template,
            user_id=user_id,
            category_id=data.category_id,
        )
        db.add(project)
        await db.flush()
        await db.refresh(project)

        # Handle tags
        if data.tag_ids:
            tag_result = await db.execute(select(Tag).where(Tag.id.in_(data.tag_ids)))
            project.tags = list(tag_result.scalars().all())

        return project

    @staticmethod
    async def get_project(db: AsyncSession, project_id: UUID) -> Project:
        """获取项目详情。"""
        project = await db.get(Project, project_id)
        if project is None or project.deleted_at is not None:
            raise ResourceNotFoundException(f"项目不存在: {project_id}")
        return project

    @staticmethod
    async def list_projects(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        user_id = None,
        is_admin: bool = False,
        category_id: str | None = None,
        tag_id: str | None = None,
    ) -> tuple[list[Project], int]:
        """分页查询项目列表。"""
        # 总数
        count_stmt = select(func.count(Project.id)).where(Project.deleted_at.is_(None))
        if not is_admin and user_id is not None:
            count_stmt = count_stmt.where(Project.user_id == user_id)
        if category_id:
            count_stmt = count_stmt.where(Project.category_id == category_id)
        if tag_id:
            count_stmt = count_stmt.where(
                Project.id.in_(
                    select(project_tag.c.project_id).where(project_tag.c.tag_id == tag_id)
                )
            )
        total = (await db.execute(count_stmt)).scalar() or 0

        # 分页数据
        stmt = (
            select(Project)
            .where(Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        if not is_admin and user_id is not None:
            stmt = stmt.where(Project.user_id == user_id)
        if category_id:
            stmt = stmt.where(Project.category_id == category_id)
        if tag_id:
            stmt = stmt.join(project_tag, project_tag.c.project_id == Project.id).where(
                project_tag.c.tag_id == tag_id
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
        project = await ProjectService.get_project(db, project_id)
        update_data = data.model_dump(exclude_unset=True)
        # Handle tags separately - need to access m2m relationship
        tag_ids = update_data.pop("tag_ids", None)
        for field, value in update_data.items():
            setattr(project, field, value)

        # Handle tags
        if tag_ids is not None:
            tag_result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
            project.tags = list(tag_result.scalars().all())

        await db.flush()
        await db.refresh(project)
        return project

    @staticmethod
    async def delete_project(db: AsyncSession, project_id: UUID) -> None:
        """软删除项目。"""
        project = await ProjectService.get_project(db, project_id)
        project.deleted_at = datetime.now(UTC)
        await db.flush()
