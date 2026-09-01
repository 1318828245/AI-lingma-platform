import { api } from "./client";

export async function getAdminOverview() {
  const { data } = await api.get("/admin/overview");
  return data;
}

export async function getAdminObservability() {
  const { data } = await api.get("/admin/observability");
  return data;
}

export async function updateAdminUser(id: number, payload: { quota?: number; status?: string }) {
  const { data } = await api.patch(`/admin/users/${id}`, payload);
  return data;
}

export async function retryAdminAssetJob(id: number) {
  const { data } = await api.post(`/admin/asset-jobs/${id}/retry`);
  return data;
}

export async function activateAdminDeployment(id: number) {
  const { data } = await api.post(`/admin/deployments/${id}/activate`);
  return data;
}

export async function offlineAdminDeployment(id: number) {
  const { data } = await api.post(`/admin/deployments/${id}/offline`);
  return data;
}

export interface AdminSettings {
  app_name: string; environment: string; register_enabled: boolean; default_user_quota: number;
  build_mode: "mock" | "real"; command_mode: "shell" | "sandbox" | "docker";
  generation_concurrency: number; modification_concurrency: number; task_timeout_seconds: number; max_requirement_length: number;
  agent_max_iterations: number; agent_max_model_steps: number; agent_max_tool_calls: number;
  agent_soft_limit_ratio: number; agent_max_no_progress_steps: number;
  llm_model: string; llm_base_url: string; llm_reasoning_effort: "low" | "medium" | "high"; llm_thinking_enabled: boolean; llm_api_key_configured: boolean;
  eval_vision_provider: "disabled" | "qwen_compatible"; eval_vision_model: string; eval_vision_base_url: string; eval_vision_thinking_enabled: boolean; eval_vision_api_key_configured: boolean;
}

export async function getAdminSettings(): Promise<AdminSettings> {
  const { data } = await api.get("/admin/settings");
  return data;
}

export async function updateAdminSettings(payload: Partial<AdminSettings>): Promise<AdminSettings> {
  const { data } = await api.put("/admin/settings", payload);
  return data;
}
