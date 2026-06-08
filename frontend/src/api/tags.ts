import apiClient from './client';

export interface TagItem {
  id: string;
  name: string;
  color: string;
  project_count: number;
  created_at: string;
}

export const getTags = () =>
  apiClient.get<TagItem[]>('/tags/');

export const createTag = (data: { name: string; color?: string }) =>
  apiClient.post<TagItem>('/tags/', data);

export const updateTag = (id: string, data: { name?: string; color?: string }) =>
  apiClient.put<TagItem>(`/tags/${id}`, data);

export const deleteTag = (id: string) =>
  apiClient.delete(`/tags/${id}`);