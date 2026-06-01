"""异步数据库引擎与会话工厂。"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.models.base import Base

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:  # type: ignore[misc]
    """FastAPI 依赖注入 — 获取异步数据库会话。"""
    async with async_session_factory() as session:
        try:
            yield session  # type: ignore[misc]
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """创建所有数据库表（开发 / 毕设用途）。

    生产环境应使用 Alembic 迁移。
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
