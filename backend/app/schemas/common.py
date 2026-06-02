"""通用 Pydantic v2 响应 Schema。"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应包装器。"""

    items: list[T] = Field(description="当前页数据列表")
    total: int = Field(description="总记录数")
    page: int = Field(ge=1, description="当前页码")
    page_size: int = Field(ge=1, le=100, description="每页大小")


class ErrorResponse(BaseModel):
    """统一错误响应。"""

    detail: str = Field(description="错误描述")
    error_code: str | None = Field(default=None, description="错误码")


class SuccessResponse(BaseModel):
    """通用成功响应。"""

    message: str = Field(description="成功消息")
    data: Any | None = Field(default=None, description="附加数据")
