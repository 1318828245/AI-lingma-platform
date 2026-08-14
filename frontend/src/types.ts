export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  status: string;
  quota: number;
  used_count: number;
}

export interface Project {
  id: number;
  owner_id: number;
  name: string;
  slug: string;
  description: string;
  template: string;
  tech_stack: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Template {
  id: number;
  name: string;
  description: string;
  tech_stack: string;
  is_active: boolean;
  file_count: number;
}

export interface Generation {
  id: number;
  project_id: number;
  session_id: number;
  status: string;
  requirement: string;
  error: string | null;
  plan_json: unknown;
  llm_model: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  build_attempt: number;
  eval_attempt: number;
  max_build_attempts: number;
  max_eval_attempts: number;
  cancel_requested: boolean;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface Message {
  id: number;
  session_id: number;
  role: string;
  content: string;
  msg_type: string;
  tool_call_json: unknown;
  created_at: string;
}

export interface ProjectFile {
  path: string;
  size: number;
  content_hash: string;
}

export interface PreviewStatus {
  status: "ready" | "not_generated" | "empty";
  mode: string;
  url: string;
}

export interface SseEvent {
  type: string;
  [key: string]: unknown;
}

export interface SessionInfo {
  id: number;
  user_id: number;
  project_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}
