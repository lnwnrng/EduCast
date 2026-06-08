"""认证业务逻辑 — 注册、登录、JWT、token 轮换。"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import AuthenticationException
from app.models.refresh_token import RefreshToken
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "access"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def _create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


class AuthService:

    @staticmethod
    async def register(
        db: AsyncSession, username: str, password: str
    ) -> tuple[User, str, str]:
        """注册新用户。返回 (user, access_token, refresh_token)。"""
        existing = await db.execute(
            select(User).where(User.username == username)
        )
        if existing.scalar_one_or_none():
            raise ValueError("用户名已存在")

        user = User(
            username=username,
            password_hash=pwd_context.hash(password),
            role="user",
        )
        db.add(user)
        await db.flush()

        access_token = _create_access_token(str(user.id))
        raw_refresh = _create_refresh_token()
        await _store_refresh_token(db, user.id, raw_refresh, None, None)
        return user, access_token, raw_refresh

    @staticmethod
    async def login(
        db: AsyncSession, username: str, password: str,
        device_info: str | None = None, ip: str | None = None,
    ) -> tuple[User, str, str]:
        """登录验证。返回 (user, access_token, refresh_token)。"""
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if not user or not pwd_context.verify(password, user.password_hash):
            raise AuthenticationException("用户名或密码错误")
        if not user.is_active:
            raise AuthenticationException("账号已被禁用")

        user.last_login = datetime.now(timezone.utc)
        access_token = _create_access_token(str(user.id))
        raw_refresh = _create_refresh_token()
        await _store_refresh_token(db, user.id, raw_refresh, device_info, ip)
        return user, access_token, raw_refresh

    @staticmethod
    async def refresh(
        db: AsyncSession, raw_refresh: str,
    ) -> tuple[User, str, str]:
        """刷新 access token + token 轮换。返回 (user, new_access_token, new_refresh_token)。"""
        token_hash = _hash_token(raw_refresh)
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked == False,  # noqa: E712
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        token_record = result.scalar_one_or_none()
        if not token_record:
            raise AuthenticationException("刷新令牌无效或已过期")

        # 轮换：撤销旧 token，创建新 token
        token_record.is_revoked = True
        user_result = await db.execute(
            select(User).where(User.id == token_record.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user or not user.is_active:
            raise AuthenticationException("用户不存在或已被禁用")

        new_access = _create_access_token(str(user.id))
        new_refresh = _create_refresh_token()
        await _store_refresh_token(
            db, user.id, new_refresh,
            token_record.device_info, token_record.ip_address,
        )
        return user, new_access, new_refresh

    @staticmethod
    async def logout(db: AsyncSession, raw_refresh: str) -> None:
        """登出：撤销 refresh token。"""
        token_hash = _hash_token(raw_refresh)
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked == False,  # noqa: E712
            )
        )
        token = result.scalar_one_or_none()
        if token:
            token.is_revoked = True

    @staticmethod
    async def get_current_user(
        db: AsyncSession, user_id: str
    ) -> User:
        """根据 user_id 查询用户。"""
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise AuthenticationException("用户不存在或已被禁用")
        return user


async def _store_refresh_token(
    db: AsyncSession,
    user_id,
    raw_token: str,
    device_info: str | None,
    ip: str | None,
) -> None:
    """持久化 refresh token。"""
    expires = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    record = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw_token),
        device_info=device_info,
        ip_address=ip,
        expires_at=expires,
    )
    db.add(record)