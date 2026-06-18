"""请求级结构化日志中间件。

记录每个 HTTP 请求的方法、路径、状态码、耗时，供运维监控与问题追踪。
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("app.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """记录每个请求的方法、路径、状态码和耗时（毫秒）。"""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        # 跳过健康检查和静态资源的高频日志
        path = request.url.path
        if path in ("/", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # 按状态码级别选择日志等级
        status = response.status_code
        if status >= 500:
            log_fn = logger.error
        elif status >= 400:
            log_fn = logger.warning
        else:
            log_fn = logger.info

        log_fn(
            "%s %s → %d (%.1fms)",
            request.method,
            path,
            status,
            elapsed_ms,
        )
        return response
