"""认证中间件测试 — Cookie 认证、require_admin。"""

import uuid

import pytest
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

# ── Cookie 认证 ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_cookie_auth_valid(auth_client: AsyncClient):
    """有效 Cookie 返回 200。"""
    resp = await auth_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testuser"


@pytest.mark.asyncio
async def test_cookie_auth_missing(client: AsyncClient):
    """无 Cookie 返回 401。"""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cookie_auth_invalid(client: AsyncClient):
    """无效 JWT 返回 401。"""
    client.cookies.set("access_token", "not-a-valid-token")
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cookie_auth_expired(db_session: AsyncSession, client: AsyncClient):
    """过期 token 返回 401。"""
    from passlib.context import CryptContext

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = User(
        id=uuid.uuid4(),
        username="expired",
        password_hash=pwd.hash("pass"),
        role="user",
        display_id=99,
    )
    db_session.add(user)
    await db_session.flush()

    from datetime import UTC, datetime, timedelta

    expired = jwt.encode(
        {
            "sub": str(user.id),
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "type": "access",
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    client.cookies.set("access_token", expired)
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ── 管理员权限 ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_endpoint_as_admin(auth_client: AsyncClient):
    """管理员访问管理端点。"""
    resp = await auth_client.get("/api/v1/admin/users?page=1&page_size=10")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_endpoint_as_user(non_admin_auth_client: AsyncClient):
    """普通用户访问管理端点应 403。"""
    resp = await non_admin_auth_client.get("/api/v1/admin/users?page=1&page_size=10")
    assert resp.status_code == 403
