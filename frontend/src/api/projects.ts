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
