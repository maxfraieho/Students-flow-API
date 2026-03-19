import axios from "axios";
import type {
  Account,
  AuditItem,
  Credential,
  HealthResponse,
  PromptItem,
  Repository,
  SettingItem,
  Student,
  SyncJob,
} from "../types";

const API_URL_KEY = "sf_api_url";
const API_TOKEN_KEY = "sf_api_token";

export function getRuntimeConfig() {
  const apiUrl =
    localStorage.getItem(API_URL_KEY)?.trim() ||
    import.meta.env.VITE_API_URL ||
    "";
  const apiToken =
    localStorage.getItem(API_TOKEN_KEY)?.trim() ||
    import.meta.env.VITE_API_TOKEN ||
    "";

  return { apiUrl: apiUrl.replace(/\/$/, ""), apiToken };
}

export function saveRuntimeConfig(apiUrl: string, apiToken: string) {
  localStorage.setItem(API_URL_KEY, apiUrl.trim());
  localStorage.setItem(API_TOKEN_KEY, apiToken.trim());
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || localStorage.getItem(API_URL_KEY) || "",
});

api.interceptors.request.use((cfg) => {
  const { apiUrl, apiToken } = getRuntimeConfig();
  cfg.baseURL = apiUrl;
  cfg.headers = cfg.headers ?? {};
  cfg.headers.Authorization = `Bearer ${apiToken}`;
  return cfg;
});

export default api;

export const healthCheck = async () => (await api.get<HealthResponse>("/api/health")).data;

export const fetchStudents = async (status?: string) => {
  const { data } = await api.get<Student[]>("/api/students", {
    params: status ? { status } : undefined,
  });
  return data;
};

export const fetchActiveStudent = async () => {
  try {
    const { data } = await api.get<Student>("/api/students/active");
    return data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) return null;
    throw error;
  }
};

export const fetchNextStudent = async () => {
  try {
    const { data } = await api.get<Student>("/api/students/next");
    return data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) return null;
    throw error;
  }
};

export const createStudent = async (payload: Partial<Student>) =>
  (await api.post<Student>("/api/students", payload)).data;

export const updateStudent = async ({ id, ...payload }: Partial<Student> & { id: string }) =>
  (await api.put<Student>(`/api/students/${id}`, payload)).data;

export const archiveStudent = async (id: string) => api.delete(`/api/students/${id}`);

export const activateStudent = async (id: string) => api.post(`/api/students/${id}/activate`);

export const bulkImportStudents = async (
  students: Array<{ full_name: string; email?: string; repo_url?: string; pat?: string; password?: string }>,
) => (await api.post("/api/students/bulk-import", { students })).data;

export const fetchAccounts = async () => (await api.get<Account[]>("/api/accounts")).data;

export const createAccount = async (payload: Partial<Account>) =>
  (await api.post<Account>("/api/accounts", payload)).data;

export const updateAccount = async ({ id, ...payload }: Partial<Account> & { id: string }) =>
  (await api.put<Account>(`/api/accounts/${id}`, payload)).data;

export const deleteAccount = async (id: string) => api.delete(`/api/accounts/${id}`);

export const setCurrentAccount = async (id: string) => api.post(`/api/accounts/${id}/set-current`);

export const markValidated = async (id: string) => api.post(`/api/accounts/${id}/mark-validated`);

export const fetchCredentials = async () => (await api.get<Credential[]>("/api/credentials")).data;

export const createCredential = async (payload: {
  account_id: string;
  auth_type?: string;
  secret?: string;
  secret_kind?: string;
  value?: string;
}) => {
  const normalized = {
    account_id: payload.account_id,
    secret_kind: payload.secret_kind || payload.auth_type || "pat",
    value: payload.value || payload.secret || "",
  };
  return (await api.post<Credential>("/api/credentials", normalized)).data;
};

export const rotateCredential = async (id: string, secret: string) =>
  api.put(`/api/credentials/${id}/rotate`, { value: secret, secret });

export const deleteCredential = async (id: string) => api.delete(`/api/credentials/${id}`);

export const checkCredentialExists = async (id: string) =>
  (await api.get<{ exists: boolean }>(`/api/credentials/${id}/exists`)).data;

export const fetchRepositories = async () => (await api.get<Repository[]>("/api/repositories")).data;

export const fetchCanonicalRepository = async () => {
  try {
    return (await api.get<Repository>("/api/repositories/canonical")).data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) return null;
    throw error;
  }
};

export const createRepository = async (payload: {
  student_id: string;
  url: string;
  branch?: string;
  local_path?: string;
}) =>
  (
    await api.post<Repository>("/api/repositories", {
      student_id: payload.student_id,
      account_id: payload.student_id,
      url: payload.url,
      remote_url: payload.url,
      branch: payload.branch,
      default_branch: payload.branch || "main",
      local_path: payload.local_path,
      repo_name: payload.url.split("/").pop()?.replace(/\.git$/, "") || "repo",
    })
  ).data;

export const updateRepository = async ({ id, ...payload }: { id: string; url: string; branch?: string; local_path?: string }) =>
  (await api.put<Repository>(`/api/repositories/${id}`, payload)).data;

export const validateRepositoryRemote = async (id: string) =>
  (await api.post<{ remote_reachable: boolean }>(`/api/repositories/${id}/validate-remote`)).data;

export const fetchRepositoryStatus = async (id: string) =>
  (await api.get<{ sync_status?: string; last_commit?: string; branch?: string }>(`/api/repositories/${id}/status`)).data;

export const fetchPrompts = async () => (await api.get<PromptItem[]>("/api/prompts")).data;

export const fetchPromptById = async (id: string) => (await api.get<PromptItem>(`/api/prompts/${id}`)).data;

export const createPrompt = async (payload: Partial<PromptItem>) =>
  (await api.post<PromptItem>("/api/prompts", payload)).data;

export const retryPrompt = async (id: string) => api.post(`/api/prompts/${id}/retry`);

export const fetchAudit = async (entity_type?: string, action?: string) =>
  (
    await api.get<AuditItem[]>("/api/audit", {
      params: {
        ...(entity_type ? { entity_type } : {}),
        ...(action ? { action } : {}),
      },
    })
  ).data;

export const fetchBackendSettings = async () => (await api.get<SettingItem[]>("/api/settings")).data;

export const putBackendSetting = async (key: string, value: string) =>
  (await api.put<SettingItem>(`/api/settings/${encodeURIComponent(key)}`, { value })).data;

export const deleteBackendSetting = async (key: string) => api.delete(`/api/settings/${encodeURIComponent(key)}`);

export const fetchSyncJobs = async () => (await api.get<SyncJob[]>("/api/sync/jobs", { params: { limit: 5 } })).data;

export const syncCurrentStudent = async () => api.post("/api/sync/current");

export const syncSpecificStudent = async (studentId: string) => api.post(`/api/sync/student/${studentId}`);

export const syncStudentToCanonical = async (studentId: string) =>
  api.post(`/api/sync/student/${studentId}/to-canonical`);

export const triggerHandoff = async () => api.post("/api/handoff");
