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

/** 资源文件的下载/预览 URL（经 Vite 代理到后端，支持 Range 流式播放）。
 *  download=false → 内联预览（<video>/<img>）；download=true → 强制下载。 */
export const getResourceDownloadUrl = (id: string, download = false) =>
  `/api/v1/resources/${id}/download${download ? '?download=true' : ''}`;
