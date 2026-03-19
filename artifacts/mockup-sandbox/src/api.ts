import type { HealthResponse, Student, SyncCurrentResponse } from "./types";

const API_URL_KEY = "sf_api_url";
const API_TOKEN_KEY = "sf_api_token";

export function getRuntimeConfig() {
  const storedUrl = localStorage.getItem(API_URL_KEY)?.trim();
  const storedToken = localStorage.getItem(API_TOKEN_KEY)?.trim();

  const apiUrl =
    storedUrl ||
    import.meta.env.VITE_API_URL ||
    window.location.origin;

  const apiToken = storedToken || import.meta.env.VITE_API_TOKEN || "";

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
  return requestJson<SyncCurrentResponse>("/api/sync/current");
}

export function getBroadcastUrl() {
  const { apiUrl, apiToken } = getRuntimeConfig();
  const url = new URL("/api/sync/broadcast", apiUrl);

  if (apiToken) {
    url.searchParams.set("token", apiToken);
  }

  return url.toString();
}
