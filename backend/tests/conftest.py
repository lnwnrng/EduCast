"""Pytest 共享 fixtures。"""

import asyncio
import uuid
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
from app.config import settings
from app.main import app
from app.models.base import Base
from app.models.user import User


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


@pytest_asyncio.fixture
async def non_admin_user(db_session: AsyncSession) -> User:
    """创建测试用普通用户（非管理员）。"""
    user = User(
        id=uuid.uuid4(),
        username="normaluser",
        password_hash="fakehash",
        role="user",
        display_id=99,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def non_admin_auth_client(
    async_engine,
    db_session: AsyncSession,
    non_admin_user: User,
) -> AsyncGenerator[AsyncClient, None]:
    """带普通用户认证 Cookie 的测试 HTTP 客户端。"""
    from jose import jwt

    test_session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    token = jwt.encode(
        {"sub": str(non_admin_user.id)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    with patch(
        "app.api.v1.upload.async_session_factory",
        test_session_factory,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.cookies.set("access_token", token)
            yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def runtime_settings_dir(tmp_path, monkeypatch):
    """将 STORAGE_ROOT 指向 tmp_path，隔离运行时设置文件 IO。"""
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    return tmp_path


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用管理员用户。"""
    user = User(
        id=uuid.uuid4(),
        username="testuser",
        password_hash="fakehash",
        role="admin",
        display_id=1,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def auth_client(
    async_engine,
    db_session: AsyncSession,
    test_user: User,
) -> AsyncGenerator[AsyncClient, None]:
    """带认证 Cookie 的测试 HTTP 客户端。"""
    from jose import jwt

    test_session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    # 生成 JWT token
    token = jwt.encode(
        {"sub": str(test_user.id)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    with patch(
        "app.api.v1.upload.async_session_factory",
        test_session_factory,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.cookies.set("access_token", token)
            yield ac

    app.dependency_overrides.clear()
