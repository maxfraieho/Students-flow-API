import axios from "axios";
import type { HealthResponse, Student } from "./types";

const API_URL_KEY = "sf_api_url";
const API_TOKEN_KEY = "sf_api_token";
const DEFAULT_API_URL = "https://studentflow-api-gateway.maxfraieho.workers.dev";

export function getRuntimeConfig() {
  const storedUrl = localStorage.getItem(API_URL_KEY)?.trim();
  const storedToken = localStorage.getItem(API_TOKEN_KEY)?.trim();

  const apiUrl = (storedUrl || import.meta.env.VITE_API_URL || DEFAULT_API_URL).replace(
    /\/$/,"",
  );
  const apiToken = storedToken || import.meta.env.VITE_API_TOKEN || "";

  return { apiUrl, apiToken };
}

export function saveRuntimeConfig(apiUrl: string, apiToken: string) {
  localStorage.setItem(API_URL_KEY, apiUrl.trim());
  localStorage.setItem(API_TOKEN_KEY, apiToken.trim());
}

const api = axios.create({
  baseURL: getRuntimeConfig().apiUrl,
});

api.interceptors.request.use((config) => {
  const { apiUrl, apiToken } = getRuntimeConfig();
  config.baseURL = apiUrl;
  config.headers = config.headers ?? {};
  config.headers.Authorization = `Bearer ${apiToken}`;
  return config;
});

export default api;

export async function getHealth() {
  const response = await api.get<HealthResponse>("/api/health");
  return response.data;
}

export async function getStudents() {
  const response = await api.get<Student[]>("/api/students");
  return response.data;
}

export async function getActiveStudent() {
  try {
    const response = await api.get<Student>("/api/students/active");
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function getNextStudent() {
  try {
    const response = await api.get<Student>("/api/students/next");
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function activateStudent(studentId: string) {
  await api.post(`/api/students/${studentId}/activate`);
}

export function getBroadcastUrl() {
  const { apiUrl, apiToken } = getRuntimeConfig();
  const url = new URL("/api/sync/broadcast", apiUrl);
  url.searchParams.set("token", apiToken);
  return url.toString();
}
