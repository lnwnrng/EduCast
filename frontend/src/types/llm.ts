/** LLM 多模型路由相关类型（与后端 schemas/llm.py 对应）。 */

export type LLMProviderType = 'claude' | 'openai' | 'glm' | 'deepseek';

export type LLMStageKey =
  | 'default'
  | 'course_metadata'
  | 'outline'
  | 'scene'
  | 'review';

export interface LLMModelInfo {
  model_id: string;
  label: string;
}

export interface LLMProviderMeta {
  provider_type: LLMProviderType;
  label: string;
  icon_key: string;
  default_base_url: string;
  default_model: string;
  supports_thinking: boolean;
  models: LLMModelInfo[];
  key_label: string;
  key_url: string;
}

export interface LLMStageMeta {
  stage_key: LLMStageKey;
  label: string;
  description: string;
}

export interface LLMProviderConfig {
  id: string;
  provider_type: LLMProviderType;
  name: string;
  base_url: string;
  model_id: string;
  is_enabled: boolean;
  sort_order: number;
  thinking_disabled: boolean;
  api_key_masked: string;
  is_configured: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface LLMStageAssignment {
  stage_key: LLMStageKey;
  config_id: string | null;
  config: LLMProviderConfig | null;
}

export interface LLMRegistry {
  providers: LLMProviderMeta[];
  stages: LLMStageMeta[];
}

export interface LLMTestResult {
  ok: boolean;
  message: string;
}

/** 新建 / 编辑 provider 配置的表单值。 */
export interface LLMConfigFormValues {
  provider_type: LLMProviderType;
  name: string;
  api_key: string;
  base_url: string;
  model_id: string;
  is_enabled: boolean;
  sort_order: number;
  thinking_disabled: boolean;
}
