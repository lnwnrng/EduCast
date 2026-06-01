"""依赖注入工厂。"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, settings
from app.database import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话。"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_settings() -> Settings:
    """获取应用配置。"""
    return settings
