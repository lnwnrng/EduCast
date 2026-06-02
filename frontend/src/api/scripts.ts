import apiClient from './client';
import type { CourseIR } from '../types/ir';

export interface ScriptResponse {
  project_id: string;
  ir: CourseIR;
}

export interface UpdateScriptResponse {
  message: string;
  data: {
    version: number;
    ir_path: string;
    validation_warnings: string[];
  };
}

/** 获取项目当前 IR 脚本 */
export const getScript = (projectId: string) =>
  apiClient.get<ScriptResponse>(`/scripts/projects/${projectId}/script`);

/** 更新 IR 脚本 */
export const updateScript = (projectId: string, irData: CourseIR) =>
  apiClient.put<UpdateScriptResponse>(
    `/scripts/projects/${projectId}/script`,
    irData
  );

/** 触发 LLM 脚本编排 */
export const generateScript = (projectId: string) =>
  apiClient.post(`/scripts/projects/${projectId}/script/generate`);

/** 审核通过脚本 */
export const approveScript = (projectId: string) =>
  apiClient.post(`/scripts/projects/${projectId}/script/approve`);
