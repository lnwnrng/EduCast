/**
 * WebSocket 进度推送 Hook
 *
 * 连接后端 WebSocket 端点，实时接收任务进度更新。
 * 替代原有 2.5s 轮询机制，体验更流畅。
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export interface ProgressUpdate {
  task_id: string;
  project_id: string;
  status: string;
  progress: number;
  error_message: string | null;
}

/**
 * 连接到项目的 WebSocket 进度推送。
 *
 * @param projectId 项目 ID，为 null 时不连接
 * @param onUpdate 收到进度更新时的回调
 */
export function useProgressWebSocket(
  projectId: string | null,
  onUpdate: (update: ProgressUpdate) => void
) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onUpdateRef = useRef(onUpdate);
  onUpdateRef.current = onUpdate;

  const connect = useCallback(() => {
    if (!projectId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/progress/${projectId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      // 启动心跳（30秒一次）
      const heartbeat = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 30000);

      ws.addEventListener('close', () => clearInterval(heartbeat));
    };

    ws.onmessage = (event) => {
      if (event.data === 'pong') return;
      try {
        const data: ProgressUpdate = JSON.parse(event.data);
        onUpdateRef.current(data);
      } catch {
        // 忽略非 JSON 消息
      }
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      // 自动重连（3秒后）
      reconnectTimerRef.current = setTimeout(() => {
        if (projectId) connect();
      }, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [projectId]);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { connected, disconnect, reconnect: connect };
}
