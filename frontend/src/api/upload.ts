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

export interface BatchUploadResponse {
  message: string;
  data: {
    items: Array<{
      project_id: string;
      task_id: string;
      filename: string;
      file_type: string;
    }>;
    total: number;
  };
}

/**
 * 上传课件文档。
 * 后端会自动创建 Project + Task 并触发后台解析。
 */
export const uploadDocument = (file: File, template: string = 'micro_lecture') => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('template', template);
  return apiClient.post<UploadResponse>('/upload/document', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  });
};

/**
 * 批量上传课件，支持多文件或 ZIP 压缩包。
 */
export const uploadBatch = (files: File[], template: string = 'micro_lecture') => {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  formData.append('template', template);
  return apiClient.post<BatchUploadResponse>('/upload/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
};
