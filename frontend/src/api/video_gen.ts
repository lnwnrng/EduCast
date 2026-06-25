import apiClient from './client';
import type {
  VideoGenConfigFormValues,
  VideoGenProviderConfig,
  VideoGenProviderMeta,
  VideoGenTestResult,
} from '../types/video_gen';

/** 获取视频生成 provider 类型静态注册表。 */
export const getVideoGenRegistry = () =>
  apiClient.get<{ providers: VideoGenProviderMeta[] }>(
    '/video-gen-providers/registry',
  );

/** 列出所有视频生成配置。 */
export const listVideoGenConfigs = () =>
  apiClient.get<VideoGenProviderConfig[]>('/video-gen-providers/configs');

/** 新建视频生成配置。 */
export const createVideoGenConfig = (data: VideoGenConfigFormValues) =>
  apiClient.post<VideoGenProviderConfig>('/video-gen-providers/configs', data);

/** 更新视频生成配置（api_key 留空表示不变）。 */
export const updateVideoGenConfig = (
  id: string,
  data: Partial<VideoGenConfigFormValues>,
) =>
  apiClient.put<VideoGenProviderConfig>(
    `/video-gen-providers/configs/${id}`,
    data,
  );

/** 删除视频生成配置。 */
export const deleteVideoGenConfig = (id: string) =>
  apiClient.delete<{ message: string }>(
    `/video-gen-providers/configs/${id}`,
  );

/** 激活一条视频生成配置（同时停用其它）。 */
export const activateVideoGenConfig = (id: string) =>
  apiClient.post<{ message: string }>(
    `/video-gen-providers/configs/${id}/activate`,
  );

/** 连通性测试。 */
export const testVideoGenConfig = (id: string) =>
  apiClient.post<VideoGenTestResult>(
    `/video-gen-providers/configs/${id}/test`,
  );
