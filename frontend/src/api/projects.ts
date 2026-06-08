import apiClient from './client';
import type { Project, ProjectCreate, ProjectUpdate } from '../types/project';

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export const getProjects = (page = 1, pageSize = 20, params?: { category_id?: string; tag_id?: string }) =>
  apiClient.get<PaginatedResponse<Project>>('/projects/', {
    params: { page, page_size: pageSize, ...params },
  });

export const getProject = (id: string) =>
  apiClient.get<Project>(`/projects/${id}`);

export const createProject = (data: ProjectCreate) =>
  apiClient.post<Project>('/projects/', data);

export const updateProject = (id: string, data: ProjectUpdate) =>
  apiClient.put<Project>(`/projects/${id}`, data);

export const deleteProject = (id: string) =>
  apiClient.delete(`/projects/${id}`);
