import type { HealthResponse, Student, SyncCurrentResponse } from "./types";

const API_URL_KEY = "sf_api_url";
const API_TOKEN_KEY = "sf_api_token";
const DEFAULT_API_URL = "https://studentflow-api-gateway.maxfraieho.workers.dev";
const LOCAL_DEV_API_URL = "http://127.0.0.1:8050";

export function getRuntimeConfig() {
  const storedUrl = localStorage.getItem(API_URL_KEY)?.trim();
  const storedToken = localStorage.getItem(API_TOKEN_KEY)?.trim();

  const isLocalDevHost =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1";

  const normalizedStoredUrl = storedUrl?.replace(/\/$/, "") || "";
  const normalizedOrigin = window.location.origin.replace(/\/$/, "");
  const useStoredUrl =
    normalizedStoredUrl.length > 0 && normalizedStoredUrl !== normalizedOrigin;
  const resolvedToken = storedToken || import.meta.env.VITE_API_TOKEN || "";

  let apiUrl =
    (useStoredUrl ? normalizedStoredUrl : "") ||
    import.meta.env.VITE_API_URL ||
    (isLocalDevHost ? LOCAL_DEV_API_URL : DEFAULT_API_URL);

  // In local dev, missing token most often means "use local backend without auth".
  if (isLocalDevHost && !resolvedToken) {
    apiUrl = LOCAL_DEV_API_URL;
  }

  const apiToken = resolvedToken;

  return { apiUrl: apiUrl.replace(/\/$/, ""), apiToken };
}

function buildUrl(path: string) {
  const { apiUrl } = getRuntimeConfig();
  return `${apiUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

async function requestJson<T>(path: string): Promise<T> {
  const { apiToken } = getRuntimeConfig();
  const response = await fetch(buildUrl(path), {
    headers: {
      "Content-Type": "application/json",
      ...(apiToken ? { Authorization: `Bearer ${apiToken}` } : {}),
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return (await response.json()) as T;
}

export function saveRuntimeConfig(apiUrl: string, apiToken: string) {
  localStorage.setItem(API_URL_KEY, apiUrl.trim());
  localStorage.setItem(API_TOKEN_KEY, apiToken.trim());
}

export async function getHealth() {
  return requestJson<HealthResponse>("/api/health");
}

export async function getStudents() {
  return requestJson<Student[]>("/api/students");
}

export async function getCurrentSync() {
  let activeStudent: Student | null = null;
  try {
    activeStudent = await requestJson<Student>("/api/students/active");
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (!message.includes("HTTP 404")) {
      throw error;
    }
  }
  return {
    active_student: activeStudent ?? null,
    sync_count_today: 0,
  } satisfies SyncCurrentResponse;
}

export function getBroadcastUrl() {
  const { apiUrl, apiToken } = getRuntimeConfig();
  const url = new URL("/api/sync/broadcast", apiUrl);

  if (apiToken) {
    url.searchParams.set("token", apiToken);
  }

  return url.toString();
}
