import { api } from "./client";
import type { ProjectVersion, VersionDiff } from "../types";

export async function listProjectVersions(projectId: number): Promise<ProjectVersion[]> {
  const { data } = await api.get(`/projects/${projectId}/versions`);
  return data;
}

export async function getProjectVersionDiff(projectId: number, versionId: number): Promise<VersionDiff> {
  const { data } = await api.get(`/projects/${projectId}/versions/${versionId}/diff`);
  return data;
}

export async function rollbackProjectVersion(projectId: number, versionId: number) {
  const { data } = await api.post(`/projects/${projectId}/versions/${versionId}/rollback`);
  return data;
}
