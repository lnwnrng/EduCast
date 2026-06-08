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