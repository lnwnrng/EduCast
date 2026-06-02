"""项目服务 — 项目 CRUD 业务逻辑。"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ResourceNotFoundException
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    """项目 CRUD 服务。"""

    @staticmethod
    async def create_project(db: AsyncSession, data: ProjectCreate) -> Project:
        """创建新项目。"""
        project = Project(
            title=data.title,
            subject=data.subject,
            grade=data.grade,
            description=data.description,
            template=data.template,
        )
        db.add(project)
        await db.flush()
        await db.refresh(project)
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
    ) -> tuple[list[Project], int]:
        """分页查询项目列表。"""
        # 总数
        count_stmt = select(func.count(Project.id)).where(Project.deleted_at.is_(None))
        total = (await db.execute(count_stmt)).scalar() or 0

        # 分页数据
        stmt = (
            select(Project)
            .where(Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
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
        for field, value in update_data.items():
            setattr(project, field, value)
        await db.flush()
        await db.refresh(project)
        return project

    @staticmethod
    async def delete_project(db: AsyncSession, project_id: UUID) -> None:
        """软删除项目。"""
        project = await ProjectService.get_project(db, project_id)
        project.deleted_at = datetime.now(UTC)
        await db.flush()
