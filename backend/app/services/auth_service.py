"""认证业务逻辑 — 注册、登录、JWT、token 轮换、邮箱验证码。"""

import hashlib
import logging
import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import AuthenticationException
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.verification_code import VerificationCode
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Access Token 黑名单（进程内）────────────────────────────
# 存储 (user_id, logout_time) 元组，用于在 logout 后拒绝旧的 access token。
# JWT 过期后（15分钟）自动从黑名单移除。进程重启时清空，但此时旧 JWT 已失效。
_access_token_blacklist: dict[str, datetime] = {}


def revoke_user_tokens(user_id: str) -> None:
    """将指定用户的所有当前 access token 加入黑名单（用于 logout）。"""
    _access_token_blacklist[user_id] = datetime.now(UTC)


def is_token_revoked(user_id: str, token_iat: datetime | None = None) -> bool:
    """检查 access token 是否在黑名单中。

    仅当用户已 logout 且 token 签发时间早于 logout 时间时才拒绝。
    自动清理已过期的黑名单条目。
    """
    revoke_time = _access_token_blacklist.get(user_id)
    if revoke_time is None:
        return False

    # 如果 token 签发时间在 revoke 时间之后，说明是新登录的 token，放行
    if token_iat and token_iat > revoke_time:
        return False

    # 自动清理：如果 revoke 时间已超过 JWT 有效期，删除条目
    if (datetime.now(UTC) - revoke_time).total_seconds() > settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60:
        del _access_token_blacklist[user_id]
        return False

    return True


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _create_access_token(user_id: str) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire, "iat": int(now.timestamp()), "type": "access"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def _create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


class AuthService:

    @staticmethod
    async def send_verification_code(
        db: AsyncSession, email: str
    ) -> int:
        """生成并发送邮箱验证码，返回冷却秒数。

        Raises:
            ValueError: 邮箱已注册、发送过于频繁等。
            ProviderException: 邮件发送失败。
        """
        # 检查邮箱是否已注册
        existing = await db.execute(
            select(User).where(User.email == email)
        )
        if existing.scalar_one_or_none():
            raise ValueError("该邮箱已被注册")

        # 频率限制：同邮箱冷却时间内只能发一次
        cooldown_threshold = datetime.now(UTC) - timedelta(
            seconds=settings.VERIFICATION_CODE_COOLDOWN_SECONDS
        )
        recent = await db.execute(
            select(VerificationCode).where(
                VerificationCode.email == email,
                VerificationCode.is_used == False,  # noqa: E712
                VerificationCode.created_at > cooldown_threshold,
            ).order_by(VerificationCode.created_at.desc())
        )
        if recent.scalars().first():
            raise ValueError("发送过于频繁，请稍后再试")

        # 生成 6 位验证码（大写字母 + 数字，排除易混淆字符 0/O/I/L）
        charset = "".join(
            c for c in string.ascii_uppercase + string.digits
            if c not in "0OIL"
        )
        code = "".join(secrets.choice(charset) for _ in range(6))

        # 创建验证码记录（hash 存储）
        expires = datetime.now(UTC) + timedelta(
            minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES
        )
        record = VerificationCode(
            email=email,
            code_hash=_hash_token(code),
            expires_at=expires,
        )
        db.add(record)
        await db.flush()

        # 发送邮件
        await EmailService.send_verification_code(email, code)

        return settings.VERIFICATION_CODE_COOLDOWN_SECONDS

    @staticmethod
    async def register(
        db: AsyncSession, username: str, password: str,
        email: str, code: str,
    ) -> tuple[User, str, str]:
        """注册新用户。返回 (user, access_token, refresh_token)。"""
        existing = await db.execute(
            select(User).where(User.username == username)
        )
        if existing.scalar_one_or_none():
            raise ValueError("用户名已存在")

        # 校验验证码
        result = await db.execute(
            select(VerificationCode).where(
                VerificationCode.email == email,
                VerificationCode.is_used == False,  # noqa: E712
                VerificationCode.expires_at > datetime.now(UTC),
            ).order_by(VerificationCode.created_at.desc())
        )
        record = result.scalars().first()
        if not record:
            raise ValueError("请先获取验证码")
        if record.attempt_count >= settings.VERIFICATION_CODE_MAX_ATTEMPTS:
            raise ValueError("验证码尝试次数过多，请重新获取")
        if _hash_token(code) != record.code_hash:
            record.attempt_count += 1
            raise ValueError("验证码错误")

        # 标记验证码已使用
        record.is_used = True

        # 检查邮箱唯一性（双重保障）
        existing_email = await db.execute(
            select(User).where(User.email == email)
        )
        if existing_email.scalar_one_or_none():
            raise ValueError("该邮箱已被注册")

        # 分配最小可用 display_id（填补删除留下的空缺）
        used_ids_result = await db.execute(
            select(User.display_id).where(User.display_id.isnot(None)).order_by(User.display_id)
        )
        used_ids = {row[0] for row in used_ids_result.all()}
        next_display_id = 1
        while next_display_id in used_ids:
            next_display_id += 1

        user = User(
            username=username,
            password_hash=pwd_context.hash(password),
            email=email,
            role="user",
            display_id=next_display_id,
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

        user.last_login = datetime.now(UTC)
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
                RefreshToken.expires_at > datetime.now(UTC),
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
        """登出：撤销 refresh token + 加入 access token 黑名单。"""
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
            # 将该用户的所有当前 access token 加入黑名单
            revoke_user_tokens(str(token.user_id))
            logger.info("用户 %s 的 access token 已加入黑名单", token.user_id)

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
    expires = datetime.now(UTC) + timedelta(
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
