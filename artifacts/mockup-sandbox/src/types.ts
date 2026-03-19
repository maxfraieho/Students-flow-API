export interface Student {
  id: string;
  full_name?: string;
  github_login?: string;
  status?: string;
  queued_at?: string;
  [key: string]: unknown;
}

export interface SyncCurrentResponse {
  active_student?: Student | null;
  queue?: Student[];
  sync_count_today?: number;
}

export interface HealthResponse {
  status?: string;
  healthy?: boolean;
  [key: string]: unknown;
}
