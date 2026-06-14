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

export interface AuditLogEntry {
  id: string;
  user_id: string;
  username: string;
  action: string;
  target_type: string;
  target_id: string | null;
  detail: string | null;
  ip_address: string | null;
  created_at: string;
}

export const getAuditLogs = (params: {
  page?: number;
  page_size?: number;
  action?: string;
  days?: number;
}) => apiClient.get<PaginatedResponse<AuditLogEntry>>('/admin/logs', { params });