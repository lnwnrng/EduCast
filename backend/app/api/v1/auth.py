"""认证 API — 注册、登录、刷新、登出、当前用户。"""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.exceptions import AuthenticationException
from app.middleware.auth import get_current_user_from_cookie
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    UserWithTokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """设置 httpOnly Cookie。"""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )


@router.post("/register", response_model=UserWithTokenResponse, status_code=201)
async def register(
    data: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserWithTokenResponse:
    """用户注册。"""
    try:
        user, access_token, refresh_token = await AuthService.register(
            db, data.username, data.password
        )
    except ValueError as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=409, detail=str(e))

    _set_auth_cookies(response, access_token, refresh_token)
    return UserWithTokenResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
    )


@router.post("/login", response_model=UserWithTokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserWithTokenResponse:
    """用户登录。"""
    user, access_token, refresh_token = await AuthService.login(
        db,
        data.username,
        data.password,
        device_info=request.headers.get("User-Agent"),
        ip=request.client.host if request.client else None,
    )
    _set_auth_cookies(response, access_token, refresh_token)
    return UserWithTokenResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
    )


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """刷新 access token（token 轮换）。"""
    raw_refresh = request.cookies.get("refresh_token")
    if not raw_refresh:
        raise AuthenticationException("缺少刷新令牌")

    user, new_access, new_refresh = await AuthService.refresh(db, raw_refresh)
    _set_auth_cookies(response, new_access, new_refresh)
    return {"message": "令牌已刷新"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """登出。"""
    raw_refresh = request.cookies.get("refresh_token")
    if raw_refresh:
        await AuthService.logout(db, raw_refresh)
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth")
    return {"message": "已登出"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user=Depends(get_current_user_from_cookie),
) -> UserResponse:
    """获取当前登录用户信息。"""
    return UserResponse.model_validate(current_user)