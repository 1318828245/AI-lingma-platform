import { api } from "./client";
import { useAuthStore } from "../stores/auth";
import type { Generation } from "../types";

export async function createGeneration(
  projectId: number,
  requirement: string,
  sessionId?: number
): Promise<Generation> {
  const { data } = await api.post(`/projects/${projectId}/generations`, {
    requirement,
    session_id: sessionId,
  });
  return data;
}

export async function getGeneration(id: number): Promise<Generation> {
  const { data } = await api.get(`/generations/${id}`);
  return data;
}

export async function getActiveGeneration(projectId: number): Promise<Generation | null> {
  const { data } = await api.get(`/projects/${projectId}/generations/active`);
  return data;
}

export async function cancelGeneration(id: number) {
  const { data } = await api.post(`/generations/${id}/cancel`);
  return data;
}

export function generationEventUrl(id: number): string {
  const auth = useAuthStore();
  return `/api/generations/${id}/events?token=${encodeURIComponent(auth.accessToken)}`;
}
