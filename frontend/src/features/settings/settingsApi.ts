import {apiJson} from "../../shared/api";

export type ProviderStatus = {
  configured: boolean;
  masked: string | null;
};

export type OllamaStatus = {
  connected: boolean;
  url: string;
};

export type ProviderSettingsResponse = {
  openai: ProviderStatus;
  openrouter: ProviderStatus;
  anthropic: ProviderStatus;
  gemini: ProviderStatus;
  mistral: ProviderStatus;
  ollama: OllamaStatus;
  workspace_env_exists: boolean;
};

export type ProviderSettingsUpdateRequest = {
  openai_api_key?: string;
  openrouter_api_key?: string;
  anthropic_api_key?: string;
  gemini_api_key?: string;
  mistral_api_key?: string;
  ollama_url?: string;
};

export async function fetchProviderSettings(token: string = ""): Promise<ProviderSettingsResponse> {
  return apiJson<ProviderSettingsResponse>("/api/settings/providers", {
    method: "GET",
    token,
  });
}

export async function saveProviderSettings(
  data: ProviderSettingsUpdateRequest,
  token: string = ""
): Promise<ProviderSettingsResponse> {
  return apiJson<ProviderSettingsResponse>("/api/settings/providers", {
    method: "POST",
    body: JSON.stringify(data),
    token,
  });
}
