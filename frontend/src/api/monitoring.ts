import apiClient from './client';
import type { CostEstimate, CostSummary, DashboardStats } from '../types/cost';

/** 全局监控面板统计 */
export const getDashboard = () =>
  apiClient.get<DashboardStats>('/monitoring/dashboard');

/** 项目成本/存储汇总 */
export const getProjectCost = (projectId: string) =>
  apiClient.get<CostSummary>(`/projects/${projectId}/cost`);

/** 项目最新 IR 的生成成本预估 */
export const getCostEstimate = (projectId: string) =>
  apiClient.get<CostEstimate>(`/projects/${projectId}/cost-estimate`);
