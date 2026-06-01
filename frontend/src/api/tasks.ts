import apiClient from './client';
import type { Task, SubTask, TaskCreate } from '../types/task';

export const createTask = (projectId: string, data: TaskCreate) =>
  apiClient.post<Task>(`/projects/${projectId}/tasks/`, data);

export const getTask = (taskId: string) =>
  apiClient.get<Task>(`/tasks/${taskId}`);

export const getSubTasks = (taskId: string) =>
  apiClient.get<SubTask[]>(`/tasks/${taskId}/subtasks`);

export const retryTask = (taskId: string) =>
  apiClient.post<Task>(`/tasks/${taskId}/retry`);
