import apiClient from './client';
import type {
  LLMConfigFormValues,
  LLMProviderConfig,
  LLMRegistry,
  LLMStageAssignment,
  LLMStageKey,
  LLMTestResult,
} from '../types/llm';

/** 获取 provider 类型与阶段的静态注册表（前端渲染图标 / 型号下拉用）。 */
export const getLLMRegistry = () =>
  apiClient.get<LLMRegistry>('/llm-providers/registry');

/** 列出所有 provider 配置（含已禁用）。 */
export const listLLMConfigs = () =>
  apiClient.get<LLMProviderConfig[]>('/llm-providers/configs');

/** 新建 provider 配置。 */
export const createLLMConfig = (data: LLMConfigFormValues) =>
  apiClient.post<LLMProviderConfig>('/llm-providers/configs', data);

/** 更新 provider 配置（api_key 留空表示不变）。 */
export const updateLLMConfig = (id: string, data: Partial<LLMConfigFormValues>) =>
  apiClient.put<LLMProviderConfig>(`/llm-providers/configs/${id}`, data);

/** 删除 provider 配置。 */
export const deleteLLMConfig = (id: string) =>
  apiClient.delete<{ message: string }>(`/llm-providers/configs/${id}`);

/** 连通性测试。 */
export const testLLMConfig = (id: string) =>
  apiClient.post<LLMTestResult>(`/llm-providers/configs/${id}/test`);

/** 列出阶段指派。 */
export const listLLMStages = () =>
  apiClient.get<LLMStageAssignment[]>('/llm-providers/stages');

/** 批量更新阶段指派。 */
export const updateLLMStages = (assignments: { stage_key: LLMStageKey; config_id: string | null }[]) =>
  apiClient.put<LLMStageAssignment[]>('/llm-providers/stages', { assignments });
