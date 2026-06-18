import apiClient from './client';

export interface Annotation {
  id: string;
  project_id: string;
  user_id: string;
  timestamp: number;
  duration: number;
  text: string;
  annotation_type: string;
  color: string;
  scene_id: string | null;
  knowledge_point_id: string | null;
  sort_order: number;
  created_at: string | null;
}

export interface AnnotationListResponse {
  message: string;
  data: {
    items: Annotation[];
    total: number;
  };
}

/** 获取项目的所有标注 */
export const listAnnotations = (projectId: string) =>
  apiClient.get<AnnotationListResponse>(`/annotations/project/${projectId}`);

/** 创建标注 */
export const createAnnotation = (data: {
  project_id: string;
  timestamp: number;
  text: string;
  duration?: number;
  annotation_type?: string;
  color?: string;
  scene_id?: string;
  knowledge_point_id?: string;
}) =>
  apiClient.post('/annotations/', null, {
    params: data,
  });

/** 更新标注 */
export const updateAnnotation = (
  annotationId: string,
  data: {
    text?: string;
    timestamp?: number;
    duration?: number;
    color?: string;
    annotation_type?: string;
  }
) => apiClient.put(`/annotations/${annotationId}`, null, { params: data });

/** 删除标注 */
export const deleteAnnotation = (annotationId: string) =>
  apiClient.delete(`/annotations/${annotationId}`);
