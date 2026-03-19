export interface Student {
  id: string;
  full_name: string;
  email?: string | null;
  status?: string;
  queue_position?: number | null;
  notes?: string | null;
  repository_id?: string | null;
  created_at?: string;
  [key: string]: unknown;
}

export interface Account {
  id: string;
  student_id: string;
  username: string;
  provider: "github" | "gitlab" | "bitbucket" | string;
  auth_type: "pat" | "ssh" | "oauth" | string;
  status?: string;
  is_current?: boolean;
  last_validated_at?: string | null;
  [key: string]: unknown;
}

export interface Credential {
  id: string;
  account_id?: string;
  auth_type?: string;
  secret_kind?: string;
  masked_secret?: string;
  secret_ref?: string;
  last_validated_at?: string | null;
  [key: string]: unknown;
}

export interface Repository {
  id: string;
  student_id?: string;
  repo_name?: string;
  url?: string;
  remote_url?: string;
  branch?: string;
  default_branch?: string;
  local_path?: string;
  sync_status?: string;
  last_commit_sha?: string;
  last_commit_hash?: string;
  last_commit_msg?: string;
  updated_at?: string;
  [key: string]: unknown;
}

export interface PromptItem {
  id: string;
  title: string;
  file_path: string;
  content: string;
  status?: string;
  pushed_at?: string | null;
  student_id?: string | null;
  [key: string]: unknown;
}

export interface AuditItem {
  id: string;
  timestamp?: string;
  actor?: string;
  action?: string;
  entity_type?: string;
  entity_id?: string;
  details?: string;
  [key: string]: unknown;
}

export interface SettingItem {
  key: string;
  value: string;
  description?: string | null;
  updated_at?: string | null;
}

export interface HealthResponse {
  status?: string;
  healthy?: boolean;
  [key: string]: unknown;
}

export interface SyncJob {
  id: string;
  status?: string;
  student_id?: string;
  summary?: string;
  error_message?: string;
  created_at?: string;
  finished_at?: string;
  [key: string]: unknown;
}
