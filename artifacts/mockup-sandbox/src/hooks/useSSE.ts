import { useEffect } from "react";
import type { Student } from "../types";

export function useSSE(onStudent: (s: Student | null) => void, onStatus: (live: boolean) => void) {
  useEffect(() => {
    const base = import.meta.env.VITE_API_URL || localStorage.getItem("sf_api_url") || "";
    const token = import.meta.env.VITE_API_TOKEN || localStorage.getItem("sf_api_token") || "";

    if (!base || !token) {
      onStatus(false);
      return;
    }

    const es = new EventSource(`${base.replace(/\/$/, "")}/api/sync/broadcast?token=${token}`);

    es.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data) as unknown;
        if (typeof payload === "object" && payload !== null) {
          if ("active_student" in payload) {
            onStudent((payload as { active_student?: Student | null }).active_student ?? null);
            return;
          }

          if ("event" in payload && (payload as { event?: string }).event === "broadcast_complete") {
            return;
          }

          if ("id" in payload) {
            onStudent(payload as Student);
          }
        }
      } catch {
        // ignore malformed events
      }
    };

    es.onopen = () => onStatus(true);
    es.onerror = () => onStatus(false);

    return () => es.close();
  }, [onStudent, onStatus]);
}
