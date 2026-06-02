"""Pytest 共享 fixtures。"""

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.deps import get_db
from app.main import app
from app.models.base import Base


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环（session 级别）。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_engine():
    """内存 SQLite 异步引擎。"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(
    async_engine,
) -> AsyncGenerator[AsyncSession, None]:
    """测试用异步数据库会话（每个测试自动回滚）。"""
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(
    async_engine,
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """测试用 HTTP 客户端（覆盖数据库依赖）。

    同时 patch async_session_factory，使后台任务也使用测试 DB。
    """
    # 为后台任务创建基于测试引擎的 session factory
    test_session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    # patch async_session_factory，让后台任务也用测试 DB
    with patch(
        "app.api.v1.upload.async_session_factory",
        test_session_factory,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()
