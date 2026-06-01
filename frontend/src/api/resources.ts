import apiClient from './client';
import type { Resource } from '../types/resource';

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

interface ResourceListParams {
  project_id?: string;
  resource_type?: string;
  page?: number;
  page_size?: number;
}

export const getResources = (params: ResourceListParams = {}) =>
  apiClient.get<PaginatedResponse<Resource>>('/resources/', { params });

export const getResource = (id: string) =>
  apiClient.get<Resource>(`/resources/${id}`);

export const deleteResource = (id: string) =>
  apiClient.delete(`/resources/${id}`);
