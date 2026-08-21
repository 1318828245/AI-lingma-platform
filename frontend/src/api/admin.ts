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
