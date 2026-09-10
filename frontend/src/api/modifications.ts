import { api } from "./client";
import { useAuthStore } from "../stores/auth";
import type { ElementSnapshot, Modification } from "../types";

export async function createModification(
  projectId: number,
  input: {
    generation_id?: number;
    session_id?: number;
    selector: Record<string, unknown>;
    element_snapshot: ElementSnapshot;
    instruction: string;
  }
): Promise<Modification> {
  const { data } = await api.post(`/projects/${projectId}/modifications`, input);
  return data;
}

export async function getModification(id: number): Promise<Modification> {
  const { data } = await api.get(`/modifications/${id}`);
  return data;
}

export async function getActiveModification(projectId: number): Promise<Modification | null> {
  const { data } = await api.get(`/projects/${projectId}/modifications/active`);
  return data;
}

export function modificationEventUrl(id: number): string {
  const auth = useAuthStore();
  return `/api/modifications/${id}/events?token=${encodeURIComponent(auth.accessToken)}`;
}

export async function cancelModification(id: number) {
  const { data } = await api.post(`/modifications/${id}/cancel`);
  return data;
}
