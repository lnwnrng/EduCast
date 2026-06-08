import apiClient from './client';

export interface CategoryNode {
  id: string;
  name: string;
  parent_id: string | null;
  sort_order: number;
  children: CategoryNode[];
  project_count: number;
  created_at: string;
}

export const getCategories = () =>
  apiClient.get<CategoryNode[]>('/categories/');

export const createCategory = (data: { name: string; parent_id?: string | null; sort_order?: number }) =>
  apiClient.post<CategoryNode>('/categories/', data);

export const updateCategory = (id: string, data: { name?: string; parent_id?: string | null; sort_order?: number }) =>
  apiClient.put<CategoryNode>(`/categories/${id}`, data);

export const deleteCategory = (id: string) =>
  apiClient.delete(`/categories/${id}`);