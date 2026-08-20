import { api } from "./client";
import type {
  PreviewStatus,
  Project,
  ProjectFile,
  SessionInfo,
  Template,
} from "../types";

export async function listProjects(): Promise<Project[]> {
  const { data } = await api.get("/projects");
  return data;
}

export async function createProject(payload: {
  name: string;
  description?: string;
  template?: string;
  tech_stack?: string;
  style_preference?: string;
}): Promise<Project> {
  const { data } = await api.post("/projects", payload);
  return data;
}

export async function getProject(id: number): Promise<Project> {
  const { data } = await api.get(`/projects/${id}`);
  return data;
}

export async function updateProject(
  id: number,
  payload: {
    name?: string;
    description?: string;
    tech_stack?: string;
    status?: string;
  }
): Promise<Project> {
  const { data } = await api.patch(`/projects/${id}`, payload);
  return data;
}

export async function deleteProject(id: number): Promise<void> {
  await api.delete(`/projects/${id}`);
}

export async function listTemplates(): Promise<Template[]> {
  const { data } = await api.get("/templates");
  return data;
}

export async function listProjectFiles(id: number): Promise<ProjectFile[]> {
  const { data } = await api.get(`/projects/${id}/files`);
  return data;
}

export async function getPreviewStatus(id: number): Promise<PreviewStatus> {
  const { data } = await api.get(`/projects/${id}/preview/status`);
  return data;
}

export async function listSessions(projectId: number): Promise<SessionInfo[]> {
  const { data } = await api.get("/sessions", {
    params: { project_id: projectId },
  });
  return data;
}

export async function listMessages(sessionId: number) {
  const { data } = await api.get(`/sessions/${sessionId}/messages`);
  return data;
}

export async function listAssetJobs(projectId: number, offset = 0, limit = 5) {
  const { data } = await api.get(`/projects/${projectId}/asset-jobs`, { params: { offset, limit } });
  return data as { jobs: AssetJob[]; total: number; next_offset: number | null };
}

export async function cancelAssetJob(projectId: number, jobId: number) {
  const { data } = await api.post(`/projects/${projectId}/asset-jobs/${jobId}/cancel`);
  return data as AssetJob;
}

export async function retryAssetJob(projectId: number, jobId: number) {
  const { data } = await api.post(`/projects/${projectId}/asset-jobs/${jobId}/retry`);
  return data as AssetJob;
}

export async function selectAssetCandidate(projectId: number, jobId: number, candidateIndex: number) {
  const { data } = await api.post(`/projects/${projectId}/asset-jobs/${jobId}/select`, { candidate_index: candidateIndex });
  return data;
}

export interface AssetJob {
  id: number;
  status: string;
  request: { kind?: string; query?: string; usage_role?: string; selected_index?: number };
  candidates: Array<{ title?: string; kind?: string; source?: string; attribution?: string; external_url?: string }>;
  error?: string | null;
}
