import { useEffect, useMemo, useState } from "react";
import {
  getBroadcastUrl,
  getCurrentSync,
  getHealth,
  getRuntimeConfig,
  getStudents,
  saveRuntimeConfig,
} from "./api";
import type { Student } from "./types";

type RoutePath = "/" | "/dashboard" | "/settings";

const navItems: Array<{ path: RoutePath; label: string }> = [
  { path: "/", label: "Головна" },
  { path: "/dashboard", label: "Дашборд" },
  { path: "/settings", label: "Налаштування" },
];

function getBasePath(): string {
  return import.meta.env.BASE_URL.replace(/\/$/, "");
}

function getRouteFromLocation(): RoutePath {
  const basePath = getBasePath();
  const pathname = window.location.pathname;
  const path = (
    basePath && pathname.startsWith(basePath)
      ? pathname.slice(basePath.length) || "/"
      : pathname
  ) as RoutePath;
  return navItems.some((item) => item.path === path) ? path : "/";
}

function formatStudentName(student: Student | null | undefined) {
  if (!student) return "—";
  return student.full_name || student.github_login || student.id;
}

function LandingPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-10 p-6 md:p-10">
      <section className="space-y-4">
        <h1 className="text-4xl font-bold tracking-tight text-foreground md:text-5xl">
          StudentFlow
        </h1>
        <p className="max-w-3xl text-lg text-muted-foreground">
          Платформа для синхронізації студентів із GitHub, моніторингу черги та
          контролю прогресу в реальному часі.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <article className="rounded-xl border border-border bg-card p-6">
          <h2 className="text-2xl font-semibold text-card-foreground">Free</h2>
          <p className="mt-2 text-muted-foreground">Базова синхронізація та черга.</p>
          <ul className="mt-4 list-disc space-y-2 pl-5 text-card-foreground">
            <li>До 100 sync/день</li>
            <li>Live статус активного студента</li>
            <li>Сторінка налаштувань API</li>
          </ul>
        </article>

        <article className="rounded-xl border border-border bg-card p-6">
          <h2 className="text-2xl font-semibold text-card-foreground">Pro</h2>
          <p className="mt-2 text-muted-foreground">
            Розширений контроль та пріоритетна обробка.
          </p>
          <ul className="mt-4 list-disc space-y-2 pl-5 text-card-foreground">
            <li>Необмежена синхронізація</li>
            <li>Детальна статистика по черзі</li>
            <li>Пріоритетна підтримка</li>
          </ul>
        </article>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <article className="rounded-xl border border-border bg-card p-6">
          <h2 className="text-xl font-semibold text-card-foreground">Завантаження</h2>
          <p className="mt-2 text-muted-foreground">Windows, macOS, Linux.</p>
        </article>
        <article className="rounded-xl border border-border bg-card p-6">
          <h2 className="text-xl font-semibold text-card-foreground">Open Source</h2>
          <p className="mt-2 text-muted-foreground">
            Повний код та інтеграції доступні для команди.
          </p>
        </article>
      </section>
    </main>
  );
}

function DashboardPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [activeStudent, setActiveStudent] = useState<Student | null>(null);
  const [syncCountToday, setSyncCountToday] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function loadData() {
      setLoading(true);
      setError(null);

      try {
        const [studentsRes, currentRes] = await Promise.all([
          getStudents(),
          getCurrentSync(),
        ]);

        if (!mounted) return;

        setStudents(studentsRes);
        setActiveStudent(currentRes.active_student ?? null);
        setSyncCountToday(currentRes.sync_count_today ?? 0);
      } catch (loadError) {
        if (!mounted) return;
        const message =
          loadError instanceof Error ? loadError.message : "Невідома помилка";
        setError(`Не вдалося завантажити дані: ${message}`);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    void loadData();

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const eventSource = new EventSource(getBroadcastUrl());

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as {
          active_student?: Student | null;
          student?: Student | null;
        };
        setActiveStudent(parsed.active_student ?? parsed.student ?? null);
      } catch {
        setActiveStudent(null);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const queue = useMemo(
    () => students.filter((student) => student.id !== activeStudent?.id),
    [students, activeStudent?.id],
  );

  const progress = Math.min(100, Math.round((syncCountToday / 100) * 100));

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-6 md:p-10">
      <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>

      {error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-destructive">
          {error}
        </div>
      )}

      <section className="grid gap-4 md:grid-cols-3">
        <article className="rounded-xl border border-border bg-card p-5">
          <p className="text-sm text-muted-foreground">Активний студент</p>
          <p className="mt-2 text-xl font-semibold text-card-foreground">
            {loading ? "Завантаження..." : formatStudentName(activeStudent)}
          </p>
        </article>

        <article className="rounded-xl border border-border bg-card p-5">
          <p className="text-sm text-muted-foreground">У черзі</p>
          <p className="mt-2 text-xl font-semibold text-card-foreground">{queue.length}</p>
        </article>

        <article className="rounded-xl border border-border bg-card p-5">
          <p className="text-sm text-muted-foreground">Sync сьогодні</p>
          <p className="mt-2 text-xl font-semibold text-card-foreground">{syncCountToday}</p>
        </article>
      </section>

      <section className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-xl font-semibold text-card-foreground">Free tier</h2>
        <p className="mt-2 text-sm text-muted-foreground">Використано {progress}% із добового ліміту.</p>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full bg-primary transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </section>

      <section className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-xl font-semibold text-card-foreground">Черга студентів</h2>
        {loading ? (
          <p className="mt-3 text-muted-foreground">Завантаження списку...</p>
        ) : queue.length === 0 ? (
          <p className="mt-3 text-muted-foreground">Черга порожня.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {queue.map((student, index) => (
              <li
                key={student.id}
                className="flex items-center justify-between rounded-lg border border-border bg-background px-3 py-2"
              >
                <span className="text-foreground">{formatStudentName(student)}</span>
                <span className="rounded-full bg-primary/10 px-2 py-1 text-xs text-primary">
                  #{index + 1}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

function SettingsPage() {
  const runtime = getRuntimeConfig();
  const [apiUrl, setApiUrl] = useState(runtime.apiUrl);
  const [apiToken, setApiToken] = useState(runtime.apiToken);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusType, setStatusType] = useState<"ok" | "error" | null>(null);

  const save = () => {
    saveRuntimeConfig(apiUrl, apiToken);
    setStatusType("ok");
    setStatusMessage("Налаштування збережено.");
  };

  const checkConnection = async () => {
    try {
      saveRuntimeConfig(apiUrl, apiToken);
      const health = await getHealth();
      const isOk = health.status === "ok" || health.healthy === true;
      setStatusType(isOk ? "ok" : "error");
      setStatusMessage(isOk ? "Зʼєднання успішне." : "Сервер відповів з помилкою.");
    } catch (checkError) {
      const message =
        checkError instanceof Error ? checkError.message : "Невідома помилка";
      setStatusType("error");
      setStatusMessage(`Помилка зʼєднання: ${message}`);
    }
  };

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-6 md:p-10">
      <h1 className="text-3xl font-bold text-foreground">Налаштування</h1>

      <section className="space-y-4 rounded-xl border border-border bg-card p-6">
        <div className="space-y-2">
          <label className="text-sm font-medium text-card-foreground" htmlFor="api-url">
            API URL
          </label>
          <input
            id="api-url"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-foreground outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
            value={apiUrl}
            onChange={(event) => setApiUrl(event.target.value)}
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-card-foreground" htmlFor="api-token">
            API Token
          </label>
          <input
            id="api-token"
            type="password"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-foreground outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
            value={apiToken}
            onChange={(event) => setApiToken(event.target.value)}
          />
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={save}
            className="rounded-md bg-primary px-4 py-2 font-medium text-primary-foreground"
          >
            Зберегти
          </button>
          <button
            type="button"
            onClick={() => void checkConnection()}
            className="rounded-md border border-border bg-secondary px-4 py-2 font-medium text-secondary-foreground"
          >
            Перевірити зʼєднання
          </button>
        </div>

        {statusMessage && (
          <p
            className={
              statusType === "ok"
                ? "text-sm text-primary"
                : "text-sm text-destructive"
            }
          >
            {statusMessage}
          </p>
        )}

        <p className="text-xs text-muted-foreground">StudentFlow v1.0 · MIT License</p>
      </section>
    </main>
  );
}

function App() {
  const [route, setRoute] = useState<RoutePath>(getRouteFromLocation());

  useEffect(() => {
    const onPopState = () => setRoute(getRouteFromLocation());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const go = (path: RoutePath) => {
    if (path === route) return;
    const basePath = getBasePath();
    const target = path === "/" ? `${basePath || "/"}` : `${basePath}${path}`;
    window.history.pushState({}, "", target);
    setRoute(path);
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
        <nav className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-2 p-4 md:p-6">
          {navItems.map((item) => (
            <button
              key={item.path}
              type="button"
              onClick={() => go(item.path)}
              className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                route === item.path
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground"
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      {(route === "/" || route === "/dashboard") && <DashboardPage />}
      {route === "/settings" && <SettingsPage />}
    </div>
  );
}

export default App;
