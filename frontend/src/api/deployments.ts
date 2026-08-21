import { api } from "./client";

export interface Deployment {
  id: number;
  project_id: number;
  version: number;
  status: "publishing" | "ready" | "failed" | "offline";
  url: string | null;
  slug: string;
  error: string | null;
  is_active: boolean;
  site_url: string | null;
  created_at: string;
  updated_at: string;
}

export async function listDeployments(projectId: number): Promise<Deployment[]> {
  const { data } = await api.get(`/projects/${projectId}/deployments`);
  return data;
}

export async function createDeployment(projectId: number, versionId?: number): Promise<Deployment> {
  const { data } = await api.post(`/projects/${projectId}/deployments`, { version_id: versionId });
  return data;
}

export async function activateDeployment(projectId: number, deploymentId: number): Promise<Deployment> {
  const { data } = await api.post(`/projects/${projectId}/deployments/${deploymentId}/activate`);
  return data;
}

export async function offlineDeployment(projectId: number, deploymentId: number): Promise<Deployment> {
  const { data } = await api.post(`/projects/${projectId}/deployments/${deploymentId}/offline`);
  return data;
}
