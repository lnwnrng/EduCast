import apiClient from './client';

export interface RequestItem {
  id: string;
  name: string;
  type: 'category' | 'tag';
  reason: string;
  status: 'pending' | 'approved' | 'rejected';
  user_id: string;
  username: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export const submitRequest = (data: { name: string; type: string; reason: string }) =>
  apiClient.post<{ message: string }>('/requests/', data);

export const getRequests = (params?: { status?: string }) =>
  apiClient.get<RequestItem[]>('/requests/', { params });

export const approveRequest = (id: string) =>
  apiClient.post<{ message: string }>(`/requests/${id}/approve`);

export const rejectRequest = (id: string) =>
  apiClient.post<{ message: string }>(`/requests/${id}/reject`);
