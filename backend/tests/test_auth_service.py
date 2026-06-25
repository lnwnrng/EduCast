"""认证服务单元测试 — 注册、登录、JWT 刷新、登出。"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AuthenticationException
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.verification_code import VerificationCode
from app.services.auth_service import AuthService, _hash_token


def _make_code(email: str, code: str = "ABC123") -> VerificationCode:
    """创建未使用的验证码记录。"""
    return VerificationCode(
        email=email,
        code_hash=_hash_token(code),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )


# ── 注册 ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_success(db_session: AsyncSession):
    """正常注册流程。"""
    db_session.add(_make_code("test@example.com"))
    await db_session.flush()

    user, access, refresh = await AuthService.register(
        db_session,
        "newuser",
        "Pass1234",
        "test@example.com",
        "ABC123",
    )
    assert user.username == "newuser"
    assert user.role == "user"
    assert user.email == "test@example.com"
    assert access
    assert refresh
    # 验证码应标记为已使用
    vc = (
        (
            await db_session.execute(
                select(VerificationCode).where(
                    VerificationCode.email == "test@example.com"
                )
            )
        )
        .scalars()
        .first()
    )
    assert vc.is_used is True


@pytest.mark.asyncio
async def test_register_duplicate_username(db_session: AsyncSession):
    """重复用户名应拒绝。"""
    db_session.add(_make_code("dup@example.com"))
    await db_session.flush()

    await AuthService.register(
        db_session,
        "dupuser",
        "Pass1234",
        "dup@example.com",
        "ABC123",
    )
    db_session.add(_make_code("dup2@example.com"))
    await db_session.flush()

    with pytest.raises(ValueError, match="用户名已存在"):
        await AuthService.register(
            db_session,
            "dupuser",
            "Pass1234",
            "dup2@example.com",
            "ABC123",
        )


@pytest.mark.asyncio
async def test_register_wrong_code(db_session: AsyncSession):
    """错误验证码应拒绝。"""
    db_session.add(_make_code("wrong@example.com", "CORRECT"))
    await db_session.flush()

    with pytest.raises(ValueError, match="验证码错误"):
        await AuthService.register(
            db_session,
            "user",
            "Pass1234",
            "wrong@example.com",
            "WRONG1",
        )


# ── 登录 ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_success(db_session: AsyncSession):
    """正常登录流程。"""
    from passlib.context import CryptContext

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = User(
        id=uuid.uuid4(),
        username="loginuser",
        password_hash=pwd.hash("Pass1234"),
        role="user",
        display_id=10,
    )
    db_session.add(user)
    await db_session.flush()

    u, access, refresh = await AuthService.login(db_session, "loginuser", "Pass1234")
    assert u.username == "loginuser"
    assert access
    assert refresh
    assert u.last_login is not None


@pytest.mark.asyncio
async def test_login_wrong_password(db_session: AsyncSession):
    """错误密码应拒绝。"""
    from passlib.context import CryptContext

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = User(
        id=uuid.uuid4(),
        username="badpw",
        password_hash=pwd.hash("Pass1234"),
        role="user",
        display_id=11,
    )
    db_session.add(user)
    await db_session.flush()

    with pytest.raises(AuthenticationException, match="用户名或密码错误"):
        await AuthService.login(db_session, "badpw", "WrongPass")


@pytest.mark.asyncio
async def test_login_disabled_user(db_session: AsyncSession):
    """已禁用用户应拒绝登录。"""
    from passlib.context import CryptContext

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = User(
        id=uuid.uuid4(),
        username="disabled",
        password_hash=pwd.hash("Pass1234"),
        role="user",
        is_active=False,
        display_id=12,
    )
    db_session.add(user)
    await db_session.flush()

    with pytest.raises(AuthenticationException, match="账号已被禁用"):
        await AuthService.login(db_session, "disabled", "Pass1234")


# ── Token 刷新 ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_success(db_session: AsyncSession):
    """正常 token 刷新（轮换）。"""
    from passlib.context import CryptContext

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = User(
        id=uuid.uuid4(),
        username="refreshuser",
        password_hash=pwd.hash("Pass1234"),
        role="user",
        display_id=13,
    )
    db_session.add(user)
    await db_session.flush()

    _, _, raw_refresh = await AuthService.login(db_session, "refreshuser", "Pass1234")

    u, new_access, new_refresh = await AuthService.refresh(db_session, raw_refresh)
    assert u.username == "refreshuser"
    assert new_access
    assert new_refresh
    # 旧 token 应被撤销
    token_hash = _hash_token(raw_refresh)
    old = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
    ).scalar_one()
    assert old.is_revoked is True


@pytest.mark.asyncio
async def test_refresh_invalid_token(db_session: AsyncSession):
    """无效 refresh token 应拒绝。"""
    with pytest.raises(AuthenticationException, match="刷新令牌无效或已过期"):
        await AuthService.refresh(db_session, "invalid-token-value")


# ── 登出 ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_logout_revokes_token(db_session: AsyncSession):
    """登出应撤销 refresh token。"""
    from passlib.context import CryptContext

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = User(
        id=uuid.uuid4(),
        username="logoutuser",
        password_hash=pwd.hash("Pass1234"),
        role="user",
        display_id=14,
    )
    db_session.add(user)
    await db_session.flush()

    _, _, raw_refresh = await AuthService.login(db_session, "logoutuser", "Pass1234")

    await AuthService.logout(db_session, raw_refresh)

    token_hash = _hash_token(raw_refresh)
    record = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
    ).scalar_one()
    assert record.is_revoked is True


# ── 验证码发送 ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_code_existing_email(db_session: AsyncSession):
    """已注册邮箱应拒绝发送验证码。"""
    user = User(
        id=uuid.uuid4(),
        username="existing",
        password_hash="hash",
        email="existing@example.com",
        role="user",
        display_id=15,
    )
    db_session.add(user)
    await db_session.flush()

    with pytest.raises(ValueError, match="该邮箱已被注册"):
        await AuthService.send_verification_code(db_session, "existing@example.com")
