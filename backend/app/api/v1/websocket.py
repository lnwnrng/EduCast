"""WebSocket 连接管理器 — 实时推送任务进度。

用法:
  前端: ws://host/api/v1/ws/progress/{project_id}
  后端: 在任务状态变更时调用 broadcast_progress()

每个 project_id 维护一组 WebSocket 连接，任务状态变更时向所有连接广播 JSON。
"""

import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])

# project_id → set of WebSocket connections
_connections: dict[str, set[WebSocket]] = defaultdict(set)


async def broadcast_progress(project_id: str, data: dict[str, Any]) -> None:
    """向指定 project_id 的所有 WebSocket 连接广播进度更新。

    data 示例: {"task_id": "...", "status": "composing", "progress": 75}
    """
    connections = _connections.get(project_id)
    if not connections:
        return

    payload = json.dumps(data, ensure_ascii=False)
    disconnected: list[WebSocket] = []

    for ws in connections:
        try:
            if ws.client_state == WebSocketState.CONNECTED:
                await ws.send_text(payload)
        except Exception:
            disconnected.append(ws)

    # 清理断开的连接
    for ws in disconnected:
        connections.discard(ws)


@router.websocket("/ws/progress/{project_id}")
async def progress_ws(websocket: WebSocket, project_id: str) -> None:
    """WebSocket 端点 — 实时推送项目任务进度。"""
    await websocket.accept()
    _connections[project_id].add(websocket)
    logger.info("WebSocket 连接建立: project=%s", project_id)

    try:
        # 保持连接，接收客户端心跳（客户端可发送 ping）
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info("WebSocket 连接断开: project=%s", project_id)
    except Exception:
        logger.debug("WebSocket 异常断开: project=%s", project_id, exc_info=True)
    finally:
        _connections[project_id].discard(websocket)
        # 清理空集合
        if not _connections[project_id]:
            del _connections[project_id]
