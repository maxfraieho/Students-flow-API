import { useEffect } from "react";
import type { Student } from "../types";

function isStudentPayload(payload: unknown): payload is Student {
  return (
    typeof payload === "object" &&
    payload !== null &&
    typeof (payload as { id?: unknown }).id === "string" &&
    typeof (payload as { full_name?: unknown }).full_name === "string"
  );
}

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

        if (typeof payload !== "object" || payload === null) return;

        if ("active_student" in payload) {
          const activeStudent = (payload as { active_student?: unknown }).active_student;
          if (activeStudent === null) {
            onStudent(null);
            return;
          }
          if (isStudentPayload(activeStudent)) {
            onStudent(activeStudent);
          }
          return;
        }

        if (isStudentPayload(payload)) {
          onStudent(payload);
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
