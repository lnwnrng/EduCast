import apiClient from './client';

export interface ApiKeyDefinition {
  key: string;
  label: string;
  description: string;
  url: string;
  features: string[];
  is_configured: boolean;
  masked_value: string;
  is_secret: boolean;
}

export const getApiKeys = () =>
  apiClient.get<{ items: ApiKeyDefinition[] }>('/settings/api-keys');

export const getApiKeyValues = () =>
  apiClient.get<{ settings: Record<string, string> }>('/settings/api-keys/values');

export const updateApiKeys = (settings: Record<string, string>) =>
  apiClient.put('/settings/api-keys', { settings });
