import apiClient from './client';
import type { WorkspaceData } from '../types/workspace';

/** 项目工作台聚合数据 */
export const getWorkspace = (projectId: string) =>
  apiClient.get<WorkspaceData>(`/projects/${projectId}/workspace`);
