"""认证相关 Pydantic 模型。"""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """注册请求。"""

    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)
    email: str = Field(..., description="注册邮箱")
    code: str = Field(..., min_length=6, max_length=6, description="邮箱验证码")


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str
    password: str


class SendCodeRequest(BaseModel):
    """发送验证码请求。"""

    email: str = Field(..., description="目标邮箱")


class SendCodeResponse(BaseModel):
    """发送验证码响应。"""

    message: str = "验证码已发送"
    cooldown_seconds: int = 60


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
