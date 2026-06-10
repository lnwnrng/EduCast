import axios from 'axios';
import { message } from 'antd';

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
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

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      // 登录/注册/验证码等认证接口返回 401 表示业务错误，不走 token 刷新
      if (
        originalRequest.url?.includes('/auth/login') ||
        originalRequest.url?.includes('/auth/register') ||
        originalRequest.url?.includes('/auth/send-code')
      ) {
        const msg = error.response?.data?.detail || error.message || '请求失败';
        message.error(msg);
        return Promise.reject(error);
      }

      // 避免 /auth/refresh 自身的 401 导致循环
      if (originalRequest.url?.includes('/auth/refresh')) {
        return Promise.reject(error);
      }

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
        // 不强制跳转，让 fetchMe 等调用方自行处理未登录状态
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