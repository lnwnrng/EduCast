"""LLM 子包共享的 httpx 连接池。"""

import httpx

from app.config import settings

# 模块级共享 httpx 连接池（避免每次调用重建 TCP 连接）
_shared_client: httpx.AsyncClient | None = None
_shared_client_loop: object | None = None


def get_shared_httpx_client(timeout: float = 60.0) -> httpx.AsyncClient:
    """获取或创建共享 httpx 客户端（带连接池复用）。

    跨事件循环自动重建（测试环境每个 test 可能有新 event loop）。
    """
    global _shared_client, _shared_client_loop  # noqa: PLW0603
    import asyncio

    current_loop = asyncio.get_running_loop()
    if (
        _shared_client is None
        or _shared_client.is_closed
        or _shared_client_loop is not current_loop
    ):
        proxy = settings.HTTP_PROXY.strip() or None
        _shared_client = httpx.AsyncClient(timeout=timeout, proxy=proxy)
        _shared_client_loop = current_loop
    return _shared_client
