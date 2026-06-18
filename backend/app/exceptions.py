"""自定义异常类与全局异常处理器。"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class EduCastException(Exception):
    """EduCast 基础异常。"""

    def __init__(
        self,
        message: str = "内部服务错误",
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class ProviderException(EduCastException):
    """Provider 适配层异常（外部 API 调用失败）。"""

    def __init__(
        self,
        message: str = "外部服务调用失败",
        error_code: str = "PROVIDER_ERROR",
        status_code: int = 502,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
        )


class ParseException(EduCastException):
    """文档解析异常。"""

    def __init__(
        self,
        message: str = "文档解析失败",
        error_code: str = "PARSE_ERROR",
        status_code: int = 422,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
        )


class CostLimitException(EduCastException):
    """成本超限异常。"""

    def __init__(
        self,
        message: str = "成本超出预算限制",
        error_code: str = "COST_LIMIT_EXCEEDED",
        status_code: int = 429,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
        )


class ResourceNotFoundException(EduCastException):
    """资源未找到异常。"""

    def __init__(
        self,
        message: str = "请求的资源不存在",
        error_code: str = "RESOURCE_NOT_FOUND",
        status_code: int = 404,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
        )


class TaskNotFoundException(EduCastException):
    """任务未找到异常。"""

    def __init__(
        self,
        message: str = "请求的任务不存在",
        error_code: str = "TASK_NOT_FOUND",
        status_code: int = 404,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
        )


class ValidationException(EduCastException):
    """数据校验异常。"""

    def __init__(
        self,
        message: str = "数据校验失败",
        error_code: str = "VALIDATION_ERROR",
        status_code: int = 422,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
        )


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


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器到 FastAPI 应用。"""

    @app.exception_handler(EduCastException)
    async def educast_exception_handler(
        request: Request,
        exc: EduCastException,
    ) -> JSONResponse:
        # 4xx 记录 warning，5xx 记录 error
        log_fn = logger.warning if exc.status_code < 500 else logger.error
        log_fn(
            "[EduCastException] %s %s → %d %s: %s",
            request.method, request.url.path,
            exc.status_code, exc.error_code, exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """全局 500 异常处理器 — 防止堆栈信息泄露。"""
        logger.error(
            "[未捕获异常] %s %s: %s",
            request.method, request.url.path, exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "服务器内部错误",
                "error_code": "INTERNAL_ERROR",
            },
        )
