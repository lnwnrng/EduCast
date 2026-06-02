import apiClient from './client';

export interface UploadResponse {
  message: string;
  data: {
    project_id: string;
    task_id: string;
    filename: string;
    file_path: string;
    file_size: number;
    file_type: string;
  };
}

/**
 * 上传课件文档。
 * 后端会自动创建 Project + Task 并触发后台解析。
 */
export const uploadDocument = (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient.post<UploadResponse>('/upload/document', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  });
};
