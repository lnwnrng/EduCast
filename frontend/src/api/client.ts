import axios from 'axios';
import { message } from 'antd';

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 响应拦截器 — 统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const msg =
      error.response?.data?.detail ||
      error.message ||
      '请求失败';
    message.error(msg);
    return Promise.reject(error);
  }
);

export default apiClient;
