/** 视频生成多模型相关类型（与后端 schemas/video_gen.py 对应）。 */

export type VideoGenProviderType = 'cogvideox' | 'kling' | 'minimax';

export interface VideoGenProviderMeta {
  provider_type: VideoGenProviderType;
  label: string;
  icon_key: string;
  default_base_url: string;
  default_model: string;
  supports_thinking: boolean;
  models: { model_id: string; label: string }[];
  key_label: string;
  key_url: string;
}

export interface VideoGenProviderConfig {
  id: string;
  provider_type: VideoGenProviderType;
  name: string;
  base_url: string;
  model_id: string;
  is_enabled: boolean;
  is_active: boolean;
  sort_order: number;
  api_key_masked: string;
  is_configured: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface VideoGenTestResult {
  ok: boolean;
  message: string;
}

export interface VideoGenConfigFormValues {
  provider_type: VideoGenProviderType;
  name: string;
  api_key: string;
  base_url: string;
  model_id: string;
  is_enabled: boolean;
  is_active: boolean;
  sort_order: number;
}
