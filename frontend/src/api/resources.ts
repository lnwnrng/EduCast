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
  search?: string;
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

/** 列出项目某文件夹下的子项（单层；网盘视图用）。parent_id 缺省=项目根。 */
export const listChildren = (projectId: string, parentId?: string) =>
  apiClient.get<Resource[]>('/resources/children', {
    params: {
      project_id: projectId,
      ...(parentId ? { parent_id: parentId } : {}),
    },
  });

/** 新建子文件夹。 */
export const createFolder = (data: {
  project_id: string;
  name: string;
  parent_id?: string | null;
}) => apiClient.post<Resource>('/resources/folders', data);

/** 重命名 / 移动资源（字段可选；parent_id 显式 null = 移回项目根）。 */
export const patchResource = (
  id: string,
  data: { name?: string; parent_id?: string | null }
) => apiClient.patch<Resource>(`/resources/${id}`, data);

export const moveResource = (id: string, parentId: string | null) =>
  patchResource(id, { parent_id: parentId });

export const renameResource = (id: string, name: string) =>
  patchResource(id, { name });
