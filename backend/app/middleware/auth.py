"""认证中间件 — 解析 JWT、注入当前用户依赖。"""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.exceptions import AuthenticationException, AuthorizationException
from app.models.user import User
from app.services.auth_service import AuthService


async def get_current_user_from_cookie(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 httpOnly Cookie 解析 access_token，返回当前用户。"""
    token = request.cookies.get("access_token")
    if not token:
        raise AuthenticationException("未登录")
    return await _verify_access_token(token, db)


async def get_current_user_from_header(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 Authorization header 解析 access_token（兼容非浏览器客户端）。"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise AuthenticationException("未登录")
    token = auth.removeprefix("Bearer ")
    return await _verify_access_token(token, db)


async def _verify_access_token(token: str, db: AsyncSession) -> User:
    from jose import JWTError, jwt

    from app.config import settings
    from app.services.auth_service import is_token_revoked

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise AuthenticationException("无效的令牌")

        # 检查 access token 是否在黑名单中（logout 后拒绝旧 token）
        iat_timestamp = payload.get("iat")
        token_iat = None
        if iat_timestamp is not None:
            from datetime import UTC, datetime
            token_iat = datetime.fromtimestamp(int(iat_timestamp), tz=UTC)
        if is_token_revoked(user_id, token_iat):
            raise AuthenticationException("令牌已失效，请重新登录")

    except JWTError:
        raise AuthenticationException("令牌无效或已过期")

    user = await AuthService.get_current_user(db, user_id)
    return user


async def require_admin(
    current_user: User = Depends(get_current_user_from_cookie),
) -> User:
    """要求当前用户为管理员。"""
    if current_user.role != "admin":
        raise AuthorizationException("需要管理员权限")
    return current_user
