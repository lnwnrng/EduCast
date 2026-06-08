# User System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user authentication (JWT dual-token, httpOnly Cookie), role-based authorization (admin/user), and admin management UI.

**Architecture:** Backend uses FastAPI with python-jose JWT + passlib bcrypt, dual-token rotation in httpOnly cookies. Frontend uses ProtectedRoute guard, Zustand for user state (no token in JS), Axios 401 interceptor for auto-refresh. Admin pages are gated by role and dynamically added to sidebar.

**Tech Stack:** Backend: python-jose, passlib[bcrypt], httpx. Frontend: Zustand (persist middleware), Ant Design Table/Tag/Dropdown, Lucide icons.

---

### [Prerequisite] Install Dependencies

- [ ] **Add python-jose + passlib to backend/requirements.txt**

Append to `backend/requirements.txt`:
```text

# Auth
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

- [ ] **Install backend dependencies**

```bash
cd backend && pip install -r requirements.txt
```
Expected: python-jose, passlib, bcrypt installed successfully.

- [ ] **Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add auth dependencies (python-jose, passlib)"
```

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/refresh_token.py`
- Create: `backend/app/models/audit_log.py`
- Modify: `backend/app/models/base.py` — add import of new models
- Modify: `backend/app/models/project.py` — add user_id FK

**Details:**
- User model: id (UUID PK), username (unique, 3-32 chars), password_hash, role ("user"|"admin", default "user"), is_active (default True), last_login (nullable), created_at, updated_at
- RefreshToken model: id (PK), user_id (FK), token_hash (sha256), device_info (nullable), ip_address (nullable), expires_at, is_revoked (default False), created_at
- AuditLog model: id (PK), user_id (FK), action, target_type (nullable), target_id (nullable), details (JSON nullable), created_at
- Project model: add user_id (FK, nullable=False), relationship to User

- [ ] **Step 1: Create user.py model**

```python
"""用户模型。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from app.models.project import Project


class User(BaseMixin, Base):
    """用户账号。"""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(16), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── 关系 ─────────────────────────────────────────────
    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
```

- [ ] **Step 2: Create refresh_token.py model**

```python
"""刷新令牌模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseMixin


class RefreshToken(BaseMixin, Base):
    """持久化刷新令牌（服务端校验用）。"""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    device_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
```

- [ ] **Step 3: Create audit_log.py model**

```python
"""审计日志模型。"""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseMixin


class AuditLog(BaseMixin, Base):
    """操作审计日志。"""

    __tablename__ = "audit_logs"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(32), index=True)
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 4: Add user_id to Project model**

Edit `backend/app/models/project.py`:
- Add `from app.models.user import User` inside TYPE_CHECKING
- Add fields:
  ```python
  user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
  owner: Mapped["User"] = relationship(back_populates="projects")
  ```
- Add `from sqlalchemy import ForeignKey` to imports

- [ ] **Step 5: Remove old DB and verify models**

```bash
rm -f backend/educast.db
cd backend && python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
```
Expected: creates all tables including users, refresh_tokens, audit_logs, and projects with user_id column.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/user.py backend/app/models/refresh_token.py backend/app/models/audit_log.py backend/app/models/project.py
git commit -m "feat: add User, RefreshToken, AuditLog models and user_id to Project"
```

---

### Task 2: Backend — Auth Schemas & Exceptions

**Files:**
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/schemas/auth.py`
- Modify: `backend/app/exceptions.py` — add auth-related exceptions

- [ ] **Step 1: Create user.py schema**

```python
"""用户 Pydantic 模型。"""

from datetime import datetime

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """用户公开信息（响应）。"""

    id: str
    username: str
    role: str
    is_active: bool
    last_login: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserAdminResponse(UserResponse):
    """管理员视角的用户信息，包含更新时间。"""

    updated_at: datetime | None = None
    project_count: int = 0
```

- [ ] **Step 2: Create auth.py schema**

```python
"""认证相关 Pydantic 模型。"""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """注册请求。"""

    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str
    password: str


class TokenResponse(BaseModel):
    """令牌响应（返回给前端，仅含 access token）。"""

    access_token: str
    token_type: str = "bearer"


class UserWithTokenResponse(BaseModel):
    """登录/注册成功响应。"""

    user: "UserResponse"
    access_token: str
    token_type: str = "bearer"


# 解决前向引用
from app.schemas.user import UserResponse  # noqa: E402, F811

UserWithTokenResponse.model_rebuild()
```

- [ ] **Step 3: Add auth exceptions**

Edit `backend/app/exceptions.py`, add before `register_exception_handlers`:

```python
class AuthenticationException(EduCastException):
    """认证失败异常（未登录或 token 无效）。"""

    def __init__(
        self,
        message: str = "未登录或登录已过期",
        error_code: str = "AUTHENTICATION_ERROR",
        status_code: int = 401,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
        )


class AuthorizationException(EduCastException):
    """权限不足异常（非管理员访问管理接口）。"""

    def __init__(
        self,
        message: str = "权限不足",
        error_code: str = "FORBIDDEN",
        status_code: int = 403,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
        )
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/user.py backend/app/schemas/auth.py backend/app/exceptions.py
git commit -m "feat: add auth schemas and exception classes"
```

---

### Task 3: Backend — Config & Auth Service

**Files:**
- Modify: `backend/app/config.py` — add JWT settings
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/middleware/auth.py`

- [ ] **Step 1: Add JWT/Cookie settings to config.py**

Add to Settings class:
```python
# ── 认证 ────────────────────────────────────────────────
JWT_SECRET_KEY: str = "change-me-to-a-real-secret-in-production"
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
REFRESH_TOKEN_EXPIRE_DAYS: int = 7
```

- [ ] **Step 2: Create auth_service.py**

```python
"""认证业务逻辑 — 注册、登录、JWT、token 轮换。"""

import hashlib
import secrets
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
        db: AsyncSession, username: str, password: str, device_info: str | None = None, ip: str | None = None
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
        db: AsyncSession, raw_refresh: str
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
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise AuthenticationException("用户不存在或已被禁用")
        return user


async def _store_refresh_token(
    db: AsyncSession,
    user_id: str,
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
```

- [ ] **Step 3: Create middleware/auth.py**

```python
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
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise AuthenticationException("无效的令牌")
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
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/config.py backend/app/services/auth_service.py backend/app/middleware/auth.py
git commit -m "feat: add auth service, JWT utils, and current-user dependency"
```

---

### Task 4: Backend — Auth API Routes

**Files:**
- Create: `backend/app/api/v1/auth.py`

- [ ] **Step 1: Create auth.py route**

```python
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


@router.post("/register", response_model=UserWithTokenResponse)
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
        db, data.username, data.password,
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
    current_user = Depends(get_current_user_from_cookie),
) -> UserResponse:
    """获取当前登录用户信息。"""
    return UserResponse.model_validate(current_user)
```

- [ ] **Step 2: Register auth router**

Edit `backend/app/api/v1/__init__.py`:
```python
from app.api.v1.auth import router as auth_router
api_v1_router.include_router(auth_router)
```

- [ ] **Step 3: Run tests to verify auth router loads**

```bash
cd backend && python -c "from app.api.v1 import api_v1_router; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/auth.py backend/app/api/v1/__init__.py
git commit -m "feat: add auth API routes (register/login/refresh/logout/me)"
```

---

### Task 5: Backend — Admin API Routes

**Files:**
- Create: `backend/app/api/v1/admin/__init__.py`
- Create: `backend/app/api/v1/admin/users.py`
- Create: `backend/app/services/audit_service.py`

- [ ] **Step 1: Create audit_service.py**

```python
"""审计日志服务。"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:

    @staticmethod
    async def log(
        db: AsyncSession,
        user_id: str,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        details: str | None = None,
    ) -> None:
        """记录一条审计日志。"""
        entry = AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
        db.add(entry)

    @staticmethod
    async def list_logs(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        action: str | None = None,
        days: int | None = None,
    ) -> tuple[list[AuditLog], int]:
        """分页查询审计日志。"""
        query = select(AuditLog)
        if action:
            query = query.where(AuditLog.action == action)
        if days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.where(AuditLog.created_at >= cutoff)
        query = query.order_by(AuditLog.created_at.desc())

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await db.execute(query)
        items = list(result.scalars().all())
        return items, total
```

- [ ] **Step 2: Create admin/__init__.py**

```python
"""Admin API 路由聚合。"""

from fastapi import APIRouter, Depends

from app.middleware.auth import require_admin
from app.api.v1.admin.users import router as users_router

admin_router = APIRouter(
    prefix="/admin",
    tags=["管理员"],
    dependencies=[Depends(require_admin)],
)

admin_router.include_router(users_router)
```

- [ ] **Step 3: Create admin/users.py**

```python
"""管理员 — 用户管理 & 审计日志。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.middleware.auth import get_current_user_from_cookie
from app.models.audit_log import AuditLog
from app.models.project import Project
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.user import UserAdminResponse
from app.services.audit_service import AuditService

router = APIRouter(tags=["用户管理"])


@router.get("/users", response_model=PaginatedResponse[UserAdminResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str | None = Query(None),
    is_active: bool | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> PaginatedResponse[UserAdminResponse]:
    """用户列表（分页 + 筛选）。"""
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if search:
        query = query.where(User.username.ilike(f"%{search}%"))
    query = query.order_by(User.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    users = list(result.scalars().all())

    items = []
    for u in users:
        pc = await db.execute(
            select(func.count()).select_from(
                select(Project).where(Project.user_id == u.id).subquery()
            )
        )
        project_count = pc.scalar() or 0
        items.append(UserAdminResponse(
            id=str(u.id),
            username=u.username,
            role=u.role,
            is_active=u.is_active,
            last_login=u.last_login,
            created_at=u.created_at,
            updated_at=u.updated_at,
            project_count=project_count,
        ))

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.patch("/users/{user_id}/role", response_model=SuccessResponse)
async def change_user_role(
    user_id: str,
    role: str = Query(..., pattern="^(admin|user)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """修改用户角色。"""
    await db.execute(
        update(User).where(User.id == user_id).values(role=role)
    )
    await AuditService.log(db, str(current_user.id), "role_change", "user", user_id, f"set role to {role}")
    return SuccessResponse(message=f"角色已更新为 {role}")


@router.patch("/users/{user_id}/toggle-active", response_model=SuccessResponse)
async def toggle_user_active(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """启用/禁用用户。"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        from app.exceptions import ResourceNotFoundException
        raise ResourceNotFoundException("用户不存在")
    if str(user.id) == str(current_user.id):
        from fastapi import HTTPException
        raise HTTPException(400, "不能禁用自己")

    user.is_active = not user.is_active
    status = "disabled" if not user.is_active else "enabled"
    await AuditService.log(db, str(current_user.id), "toggle_active", "user", user_id, status)
    return SuccessResponse(message=f"用户已{'禁用' if not user.is_active else '启用'}")


@router.delete("/users/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> SuccessResponse:
    """删除用户。"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        from app.exceptions import ResourceNotFoundException
        raise ResourceNotFoundException("用户不存在")
    if str(user.id) == str(current_user.id):
        from fastapi import HTTPException
        raise HTTPException(400, "不能删除自己")

    await db.delete(user)
    await AuditService.log(db, str(current_user.id), "delete_user", "user", user_id)
    return SuccessResponse(message="用户已删除")


@router.get("/logs", response_model=PaginatedResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = Query(None),
    days: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
) -> PaginatedResponse:
    """审计日志列表。"""
    from app.schemas.common import PaginatedResponse as PR
    items, total = await AuditService.list_logs(db, page, page_size, action, days)
    return PR(
        items=[{
            "id": str(log.id),
            "user_id": str(log.user_id),
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        } for log in items],
        total=total,
        page=page,
        page_size=page_size,
    )
```

- [ ] **Step 4: Register admin router in main.py**

Edit `backend/app/main.py`, after the import of `api_v1_router`:
```python
from app.api.v1.admin import admin_router  # noqa: E402
app.include_router(admin_router, prefix="/api/v1")
```

- [ ] **Step 5: Verify imports**

```bash
cd backend && python -c "from app.main import app; print('OK')"
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/admin/ backend/app/services/audit_service.py backend/app/main.py
git commit -m "feat: add admin API (user management + audit logs)"
```

---

### Task 6: Backend — Project User Isolation

**Files:**
- Modify: `backend/app/api/v1/projects.py` — add user filtering
- Modify: `backend/app/services/project_service.py` — add user_id on create

- [ ] **Step 1: Read current project service to understand patterns**

- [ ] **Step 2: Add current_user dependency to project routes**

Edit `backend/app/api/v1/projects.py`:
- Add imports: `from app.middleware.auth import get_current_user_from_cookie`, `from app.models.user import User`
- Add `current_user: User = Depends(get_current_user_from_cookie)` to each route
- In `create_project`: pass `current_user` to service
- In `list_projects`: pass `current_user` to service for filtering
- Add permission check in `get_project`/`update_project`/`delete_project`: only admin or owner

- [ ] **Step 3: Update ProjectService.create_project**

Pass `user_id: str` param, set `project.user_id = user_id`

- [ ] **Step 4: Update ProjectService.list_projects**

Add `user_id: str | None` and `is_admin: bool` params. When not admin, filter by `Project.user_id == user_id`.

- [ ] **Step 5: Verify**

```bash
cd backend && python -c "from app.main import app; print('OK')"
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/projects.py backend/app/services/project_service.py
git commit -m "feat: add user isolation to project CRUD"
```

---

### Task 7: Frontend — Auth Types & API Client

**Files:**
- Create: `frontend/src/types/user.ts`
- Create: `frontend/src/api/auth.ts`
- Modify: `frontend/src/api/client.ts` — add 401 interceptor

- [ ] **Step 1: Create user.ts type**

```typescript
export interface User {
  id: string;
  username: string;
  role: 'admin' | 'user';
  is_active: boolean;
  last_login: string | null;
  created_at: string;
}

export interface UserAdmin extends User {
  updated_at: string | null;
  project_count: number;
}

export interface UserWithToken {
  user: User;
  access_token: string;
  token_type: string;
}
```

- [ ] **Step 2: Create api/auth.ts**

```typescript
import apiClient from './client';
import type { UserWithToken, User } from '../types/user';

export const register = (username: string, password: string) =>
  apiClient.post<UserWithToken>('/auth/register', { username, password });

export const login = (username: string, password: string) =>
  apiClient.post<UserWithToken>('/auth/login', { username, password });

export const refreshToken = () =>
  apiClient.post<{ message: string }>('/auth/refresh');

export const logout = () =>
  apiClient.post<{ message: string }>('/auth/logout');

export const getMe = () =>
  apiClient.get<User>('/auth/me');
```

- [ ] **Step 3: Update api/client.ts — add 401 interceptor**

```typescript
import axios from 'axios';
import { message } from 'antd';

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // 发送 httpOnly Cookie
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason: unknown) => void;
}> = [];

const processQueue = (error: unknown) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(undefined);
    }
  });
  failedQueue = [];
};

// 响应拦截器 — 统一错误处理 + 401 自动刷新
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => apiClient(originalRequest));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        await apiClient.post('/auth/refresh');
        processQueue(null);
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError);
        // 清除用户状态，跳转登录页
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    const msg =
      error.response?.data?.detail ||
      error.message ||
      '请求失败';
    if (error.response?.status !== 401) {
      message.error(msg);
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/user.ts frontend/src/api/auth.ts frontend/src/api/client.ts
git commit -m "feat: add auth types, API, and Axios 401 auto-refresh interceptor"
```

---

### Task 8: Frontend — Auth Store & ProtectedRoute

**Files:**
- Create: `frontend/src/stores/authStore.ts`
- Create: `frontend/src/components/Auth/ProtectedRoute.tsx`

- [ ] **Step 1: Create authStore.ts**

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../types/user';
import * as authApi from '../api/auth';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchMe: () => Promise<void>;
  setUser: (user: User | null) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true,

      login: async (username, password) => {
        const { data } = await authApi.login(username, password);
        set({ user: data.user, isAuthenticated: true });
      },

      register: async (username, password) => {
        const { data } = await authApi.register(username, password);
        set({ user: data.user, isAuthenticated: true });
      },

      logout: async () => {
        try {
          await authApi.logout();
        } catch {
          // 即使接口失败也清除本地状态
        }
        set({ user: null, isAuthenticated: false });
      },

      fetchMe: async () => {
        try {
          const { data } = await authApi.getMe();
          set({ user: data, isAuthenticated: true, isLoading: false });
        } catch {
          set({ user: null, isAuthenticated: false, isLoading: false });
        }
      },

      setUser: (user) =>
        set({ user, isAuthenticated: !!user }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
```

- [ ] **Step 2: Create ProtectedRoute.tsx**

```tsx
import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuthStore } from '../../stores/authStore';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireAdmin = false,
}) => {
  const { isAuthenticated, isLoading, user } = useAuthStore();
  const location = useLocation();

  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireAdmin && user?.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/authStore.ts frontend/src/components/Auth/ProtectedRoute.tsx
git commit -m "feat: add auth store with persist and ProtectedRoute component"
```

---

### Task 9: Frontend — Login & Register Pages

**Files:**
- Create: `frontend/src/pages/Login/index.tsx`
- Create: `frontend/src/pages/Register/index.tsx`

- [ ] **Step 1: Create Login page**

```tsx
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, Typography, message } from 'antd';
import { useAuthStore } from '../../stores/authStore';

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const handleSubmit = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success('登录成功');
      navigate('/', { replace: true });
    } catch (err: any) {
      // 错误已在 Axios 拦截器中 toast
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        height: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: 'linear-gradient(135deg, #f0f5ff 0%, #f8fafd 100%)',
      }}
    >
      <div
        style={{
          width: 400,
          padding: '40px 32px',
          background: '#fff',
          borderRadius: 24,
          boxShadow: '0 8px 24px rgba(0,0,0,0.04)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <span
            style={{
              fontFamily: '"Dancing Script", cursive',
              fontSize: 36,
              color: '#333',
              fontWeight: 600,
            }}
          >
            EduCast
          </span>
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            智能教学视频生产平台
          </Text>
        </div>

        <Form onFinish={handleSubmit} layout="vertical" size="large">
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="请输入用户名" />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password placeholder="请输入密码" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登 录
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">还没有账号？</Text>
          <Link to="/register" style={{ color: '#1677ff', marginLeft: 4 }}>
            立即注册
          </Link>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
```

- [ ] **Step 2: Create Register page** (similar to Login, with username + password + confirm password, navigate to / on success)

```tsx
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, Typography, message } from 'antd';
import { useAuthStore } from '../../stores/authStore';

const { Text } = Typography;

const RegisterPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const register = useAuthStore((s) => s.register);
  const navigate = useNavigate();

  const handleSubmit = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await register(values.username, values.password);
      message.success('注册成功');
      navigate('/', { replace: true });
    } catch {
      // handled by axios interceptor
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        height: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: 'linear-gradient(135deg, #f0f5ff 0%, #f8fafd 100%)',
      }}
    >
      <div
        style={{
          width: 400,
          padding: '40px 32px',
          background: '#fff',
          borderRadius: 24,
          boxShadow: '0 8px 24px rgba(0,0,0,0.04)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <span
            style={{
              fontFamily: '"Dancing Script", cursive',
              fontSize: 36,
              color: '#333',
              fontWeight: 600,
            }}
          >
            EduCast
          </span>
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            创建新账号
          </Text>
        </div>

        <Form onFinish={handleSubmit} layout="vertical" size="large">
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '至少3个字符' },
              { max: 32, message: '最多32个字符' },
              { pattern: /^[a-zA-Z0-9_]+$/, message: '仅支持字母、数字和下划线' },
            ]}
          >
            <Input placeholder="3-32位字母数字下划线" />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 8, message: '密码至少8位' },
            ]}
          >
            <Input.Password placeholder="至少8位密码" />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            label="确认密码"
            dependencies={['password']}
            rules={[
              { required: true, message: '请确认密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="再次输入密码" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              注 册
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">已有账号？</Text>
          <Link to="/login" style={{ color: '#1677ff', marginLeft: 4 }}>
            立即登录
          </Link>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Login/index.tsx frontend/src/pages/Register/index.tsx
git commit -m "feat: add login and register pages"
```

---

### Task 10: Frontend — Route & Layout Updates

**Files:**
- Modify: `frontend/src/App.tsx` — add auth routes + ProtectedRoute
- Modify: `frontend/src/components/Layout/AppLayout.tsx` — dynamic menu + user dropdown

- [ ] **Step 1: Update App.tsx**

Wrap existing AppLayout routes with ProtectedRoute, add login/register outside:

```tsx
import { Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import AppLayout from './components/Layout/AppLayout';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import LoginPage from './pages/Login';
import RegisterPage from './pages/Register';
// ... other imports
import UserManagement from './pages/Admin/UserManagement';
import AuditLog from './pages/Admin/AuditLog';
import { useAuthStore } from './stores/authStore';

const App: React.FC = () => {
  const fetchMe = useAuthStore((s) => s.fetchMe);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  return (
    <Routes>
      {/* 公开路由 */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* 受保护路由 */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/workspace" element={<Workspace />} />
        <Route path="/projects/:id" element={<Workspace />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/projects/:id/upload" element={<UploadPage />} />
        <Route path="/script" element={<ScriptEditor />} />
        <Route path="/projects/:id/script" element={<ScriptEditor />} />
        <Route path="/preview" element={<Preview />} />
        <Route path="/projects/:id/preview" element={<Preview />} />
        <Route path="/resources" element={<Resources />} />
        <Route path="/monitoring" element={<Monitoring />} />
      </Route>

      {/* Admin 路由 */}
      <Route
        element={
          <ProtectedRoute requireAdmin>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/admin/users" element={<UserManagement />} />
        <Route path="/admin/logs" element={<AuditLog />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};
```

- [ ] **Step 2: Update AppLayout.tsx — dynamic menu**

Add to imports:
```typescript
import { Users, FileText, LogOut, User as UserIcon } from 'lucide-react';
import { Dropdown, Avatar, Space } from 'antd';
import { useAuthStore } from '../../stores/authStore';
import { useNavigate } from 'react-router-dom';
```

In the component body:
```typescript
const { user, logout } = useAuthStore();

const menuItems = [
  // ... existing items
  // Add admin-only items
  ...(user?.role === 'admin'
    ? [
        { type: 'divider' as const },
        {
          key: '/admin/users',
          icon: <Users size={20} strokeWidth={1.5} />,
          label: '用户管理',
        },
        {
          key: '/admin/logs',
          icon: <FileText size={20} strokeWidth={1.5} />,
          label: '审计日志',
        },
      ]
    : []),
];

// Add user dropdown in Header
const userMenuItems = [
  {
    key: 'logout',
    icon: <LogOut size={16} />,
    label: '退出登录',
    onClick: async () => {
      await logout();
      navigate('/login');
    },
  },
];
```

Add user avatar/dropdown next to the header title:
```tsx
<div style={{ marginLeft: 'auto', paddingRight: 24 }}>
  <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
    <Space style={{ cursor: 'pointer' }}>
      <Avatar size={32} style={{ backgroundColor: '#1677ff' }}>
        {user?.username?.[0]?.toUpperCase()}
      </Avatar>
      <span style={{ color: '#333' }}>{user?.username}</span>
    </Space>
  </Dropdown>
</div>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Layout/AppLayout.tsx
git commit -m "feat: add auth routing, ProtectedRoute, dynamic menu, and user dropdown"
```

---

### Task 11: Frontend — Admin Pages

**Files:**
- Create: `frontend/src/pages/Admin/UserManagement.tsx`
- Create: `frontend/src/pages/Admin/AuditLog.tsx`
- Create: `frontend/src/api/admin.ts`

- [ ] **Step 1: Create api/admin.ts**

```typescript
import apiClient from './client';
import type { UserAdmin } from '../types/user';

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export const getUsers = (params: {
  page?: number;
  page_size?: number;
  role?: string;
  is_active?: boolean;
  search?: string;
}) => apiClient.get<PaginatedResponse<UserAdmin>>('/admin/users', { params });

export const changeUserRole = (userId: string, role: string) =>
  apiClient.patch(`/admin/users/${userId}/role`, null, { params: { role } });

export const toggleUserActive = (userId: string) =>
  apiClient.patch(`/admin/users/${userId}/toggle-active`);

export const deleteUser = (userId: string) =>
  apiClient.delete(`/admin/users/${userId}`);

export const getAuditLogs = (params: {
  page?: number;
  page_size?: number;
  action?: string;
  days?: number;
}) => apiClient.get<PaginatedResponse<any>>('/admin/logs', { params });
```

- [ ] **Step 2: Create UserManagement.tsx**

Full page with Ant Design Table, search input, role/status filters, action buttons (change role, toggle active, delete). Use the same white-card-container style as other pages.

- [ ] **Step 3: Create AuditLog.tsx**

Full page with Ant Design Table showing logs, with filters for action type and time range.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Admin/ frontend/src/api/admin.ts
git commit -m "feat: add admin pages (user management + audit logs)"
```

---

### Task 12: End-to-End Smoke Test

**Files:** (no changes — just verification)

- [ ] **Step 1: Start backend and test auth endpoints**

```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

In another terminal:
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}' \
  -v
# Expected: 201, cookies set, user returned

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}' \
  -v
# Expected: 200, cookies set

# Get Me (with cookies)
curl -X GET http://localhost:8000/api/v1/auth/me \
  -b cookies.txt
# Expected: 200, user info

# Admin-only (should fail)
curl -X GET http://localhost:8000/api/v1/admin/users \
  -b cookies.txt
# Expected: 403
```

- [ ] **Step 2: Start frontend and test UI flow**

```bash
cd frontend && npx vite --port 5173
```

Test flow:
1. Visit http://localhost:5173 — should redirect to /login
2. Click "立即注册" — navigate to /register
3. Register a new user — should redirect to / with user logged in
4. Sidebar should show no admin menu items
5. Logout via user dropdown — should return to /login
6. Login as admin (need to manually set role in DB) — sidebar should show "用户管理" and "审计日志"
7. Visit /admin/users — should see user table

- [ ] **Step 3: Commit any final fixes**

```bash
git commit -m "fix: post-auth-test adjustments"
```