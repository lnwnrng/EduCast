import apiClient from './client';
import type { Project, ProjectCreate, ProjectUpdate } from '../types/project';

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export const getProjects = (
  page = 1,
  pageSize = 20,
  params?: { category_id?: string; tag_ids?: string[] }
) =>
  apiClient.get<PaginatedResponse<Project>>('/projects/', {
    params: {
      page,
      page_size: pageSize,
      ...(params?.category_id && { category_id: params.category_id }),
      ...(params?.tag_ids?.length && { tag_ids: params.tag_ids.join(',') }),
    },
  });

export const getProject = (id: string) =>
  apiClient.get<Project>(`/projects/${id}`);

export const createProject = (data: ProjectCreate) =>
  apiClient.post<Project>('/projects/', data);

export const updateProject = (id: string, data: ProjectUpdate) =>
  apiClient.put<Project>(`/projects/${id}`, data);

export const deleteProject = (id: string) =>
  apiClient.delete(`/projects/${id}`);

export interface KnowledgeGraphData {
  nodes: Array<{
    id: string;
    title: string;
    chapter: string;
    chapter_order: number;
    tags: string[];
    key_points: string[];
  }>;
  edges: Array<{
    source: string;
    target: string;
    tag: string;
  }>;
}

export const getKnowledgeGraph = (projectId: string) =>
  apiClient.get<KnowledgeGraphData>(`/projects/${projectId}/knowledge-graph`);

export interface AssessmentData {
  chapters: Array<{
    chapter_id: string;
    title: string;
    questions: Array<{
      kp_id: string;
      kp_title: string;
      question: string;
      question_type: string;
      answer: string;
      explanation: string;
    }>;
  }>;
}

export const getAssessment = (projectId: string) =>
  apiClient.get<AssessmentData>(`/projects/${projectId}/assessment`);

export interface VersionCompareData {
  v1: number;
  v2: number;
  chapter_count: { v1: number; v2: number };
  kp_count: { v1: number; v2: number };
  added: Array<{ id: string; title: string; chapter: string }>;
  removed: Array<{ id: string; title: string; chapter: string }>;
  modified: Array<{ id: string; title: string; changes: string[] }>;
  summary: string;
}

export const compareVersions = (projectId: string, v1: number, v2: number) =>
  apiClient.get<VersionCompareData>(`/projects/${projectId}/versions/compare`, {
    params: { v1, v2 },
  });
