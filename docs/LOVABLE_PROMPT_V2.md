# Lovable Prompt V2 — StudentFlow (Повний функціонал)

Вставте цей промт у Lovable після імпорту репозиторію.

---

## PROMPT (paste into Lovable chat)

Build a complete **StudentFlow** operator web application — a full management dashboard
for a teacher who controls ~20 students doing sequential Git repository sync sessions.
This is a web port of a PySide6 desktop app, so all features must be functional.

---

### Tech Stack
- React + TypeScript + Vite (already set up)
- **Material UI (MUI v5)** — Material Design everywhere
- React Query (`@tanstack/react-query`) for all data fetching and mutations
- Axios for REST API calls
- Native `EventSource` for SSE

### Environment & API Client

Create `src/api/client.ts`:
```typescript
import axios from 'axios';
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || localStorage.getItem('sf_api_url') || '',
});
api.interceptors.request.use(cfg => {
  const token = import.meta.env.VITE_API_TOKEN || localStorage.getItem('sf_api_token') || '';
  cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});
export default api;
```

---

### Layout: Shell

`src/App.tsx` — persistent MUI shell:
- **AppBar** (top, always visible):
  - Left: hamburger icon + "StudentFlow" title
  - Right: SSE live status `Chip` (green dot "Онлайн" / grey "Офлайн") + settings icon
- **Drawer** (left sidebar, 240px, permanent on desktop, temporary on mobile):
  - Navigation `List` with these items in order:
    1. `Dashboard` icon: `Dashboard`
    2. `Студенти` icon: `People`
    3. `Акаунти` icon: `ManageAccounts`
    4. `Облікові дані` icon: `Key`
    5. `Репозиторії` icon: `FolderSpecial`
    6. `Промти` icon: `Psychology`
    7. `Журнал` icon: `History`
    8. divider
    9. `Налаштування` icon: `Settings`
- **Main content** area with React Router routes

---

### Route Map

| Path | Component |
|------|-----------|
| `/` | redirect → `/dashboard` |
| `/dashboard` | `DashboardPage` |
| `/students` | `StudentsPage` |
| `/accounts` | `AccountsPage` |
| `/credentials` | `CredentialsPage` |
| `/repositories` | `RepositoriesPage` |
| `/prompts` | `PromptsPage` |
| `/audit` | `AuditPage` |
| `/settings` | `SettingsPage` |

---

### Full API Reference

Base URL = `VITE_API_URL`. All requests: `Authorization: Bearer <token>`.

#### Students — `/api/students`
| Method | Path | Body / Notes |
|--------|------|--------------|
| GET | `/api/students` | `?status=active\|paused\|archived` optional filter |
| GET | `/api/students/active` | current active student |
| GET | `/api/students/next` | next in queue |
| GET | `/api/students/{id}` | single student |
| POST | `/api/students` | `{full_name, email?, notes?, queue_position?}` |
| PUT | `/api/students/{id}` | same fields, partial |
| DELETE | `/api/students/{id}` | archives (status→archived) |
| POST | `/api/students/{id}/activate` | make active |
| POST | `/api/students/bulk-import` | `{students: [{full_name, email, repo_url, pat, password?}]}` |

Student object: `{id, full_name, email, status, queue_position, notes, repository_id, created_at}`
Statuses: `active` (green), `paused` (yellow), `exhausted` (grey), `error` (red), `archived` (dark grey)

#### Accounts — `/api/accounts`
| Method | Path | Body |
|--------|------|------|
| GET | `/api/accounts` | |
| GET | `/api/accounts/{id}` | |
| POST | `/api/accounts` | `{student_id, username, provider, auth_type}` |
| PUT | `/api/accounts/{id}` | partial |
| DELETE | `/api/accounts/{id}` | deactivates |
| POST | `/api/accounts/{id}/set-current` | mark as student's active account |
| POST | `/api/accounts/{id}/mark-validated` | |

Account object: `{id, student_id, username, provider, auth_type, status, last_validated_at}`
Providers: `github`, `gitlab`, `bitbucket`
Auth types: `pat`, `ssh`, `oauth`

#### Credentials — `/api/credentials`
| Method | Path | Body |
|--------|------|------|
| GET | `/api/credentials` | |
| POST | `/api/credentials` | `{account_id, auth_type, secret}` |
| PUT | `/api/credentials/{id}/rotate` | `{secret}` — rotate PAT |
| DELETE | `/api/credentials/{id}` | |
| GET | `/api/credentials/{id}/exists` | `{exists: bool}` |

Credential object: `{id, account_id, auth_type, masked_secret, last_validated_at}`
Note: never show raw secrets — always show `masked_secret` (format: `ghp_****...xxxx`)

#### Repositories — `/api/repositories`
| Method | Path | Body |
|--------|------|------|
| GET | `/api/repositories` | |
| GET | `/api/repositories/canonical` | canonical repo info |
| GET | `/api/repositories/{id}` | |
| POST | `/api/repositories` | `{student_id, url, branch?, local_path?}` |
| POST | `/api/repositories/{id}/validate-remote` | |
| GET | `/api/repositories/{id}/status` | `{sync_status, last_commit, branch}` |

Repo object: `{id, student_id, url, branch, local_path, sync_status, last_commit_sha, last_commit_msg}`
Sync statuses: `clean` (green), `dirty` (yellow), `diverged` (orange), `error` (red), `uninitialized` (grey)

#### Handoff — `/api/handoff`
| Method | Path | Body |
|--------|------|------|
| GET | `/api/handoff/events` | list handoff events |
| GET | `/api/handoff/events/{id}` | |
| POST | `/api/handoff` | trigger handoff (complete current → activate next) |

#### Prompts — `/api/prompts`
| Method | Path | Body |
|--------|------|------|
| GET | `/api/prompts` | |
| GET | `/api/prompts/{id}` | |
| POST | `/api/prompts` | `{title, file_path, content, student_id?}` |
| POST | `/api/prompts/{id}/retry` | retry failed push |

Prompt object: `{id, title, file_path, content, status, pushed_at, student_id}`
Statuses: `pushed` (green), `committed` (teal), `written` (orange), `draft` (grey), `failed` (red)

#### Audit — `/api/audit`
| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/audit` | `?entity_type=&action=` filters |

Audit object: `{id, timestamp, actor, action, entity_type, entity_id, details}`

#### Settings — `/api/settings`
| Method | Path | Body |
|--------|------|------|
| GET | `/api/settings` | all key-value pairs |
| GET | `/api/settings/{key}` | |
| PUT | `/api/settings/{key}` | `{value}` |
| DELETE | `/api/settings/{key}` | |

#### Sync — `/api/sync`
| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/sync/broadcast` | SSE stream (`?token=TOKEN`) |
| GET | `/api/sync/jobs` | list recent sync jobs |
| POST | `/api/sync/current` | trigger sync for active student |
| POST | `/api/sync/student/{id}` | trigger sync for specific student |

---

### Page 1: Dashboard (`/dashboard`)

Two-column layout (3:1 ratio on desktop, stacked on mobile).

**Left column:**

`QGroupBox` → MUI `Paper` with title "Активний студент":
- Large `Avatar` (80px) with student initials
- Typography h5: student `full_name`
- `Chip` with status color
- `FormLabel` rows: Email, Queue Position, Notes
- Action buttons row:
  - "Синхронізувати" (POST `/api/sync/current`) — contained primary
  - "Наступний студент" (POST `/api/handoff`) — contained secondary
  - "Деталі" → navigate to `/students`

Below that: `Paper` "Остання активність":
- MUI `List` of sync jobs from `GET /api/sync/jobs` (last 5)
- Each item: icon (check=success, ×=failed, ⟳=running) + timestamp + status chip

**Right column:**

`Paper` "Черга":
- Numbered `List` of all non-archived students sorted by `queue_position`
- Each item: position badge + initials Avatar + full_name + status chip
- Click → `/students`

`Paper` "Канонічне репо" (data from `GET /api/repositories/canonical`):
- Local path
- Branch
- Last sync time

---

### Page 2: Студенти (`/students`)

**Toolbar:**
- `Button` "+ Додати студента" → opens add dialog
- `Button` "Bulk Import" → opens CSV/JSON paste dialog
- `Button` "Оновити"
- `TextField` search/filter (filters table client-side by name)

**MUI `DataGrid`** (or MUI `Table`) with columns:
| Column | Notes |
|--------|-------|
| # | queue_position |
| Повне ім'я | full_name, clickable → edit dialog |
| Статус | colored `Chip`: active=green, paused=yellow, exhausted=grey, error=red, archived=darkgrey |
| Позиція черги | queue_position number |
| Нотатки | notes text, truncated |
| Дії | icon buttons: Edit ✏️, Activate ▶️, Archive 🗑️ |

**Add/Edit Student Dialog** (MUI `Dialog`):
- `TextField` "Повне ім'я" (required)
- `TextField` "Email"
- `TextField` "Нотатки" multiline
- `TextField` number "Позиція черги"
- Save / Cancel buttons

**Bulk Import Dialog**:
- `TextField` multiline — paste JSON array:
  ```json
  [{"full_name":"...", "repo_url":"...", "pat":"..."}]
  ```
- Shows result table after import (created/skipped per student)

---

### Page 3: Акаунти (`/accounts`)

**Toolbar:** "+ Додати акаунт", "Оновити"

**MUI Table** columns:
| Column | Notes |
|--------|-------|
| Логін | username |
| Провайдер | github/gitlab/bitbucket — with icon |
| Тип авт. | pat/ssh/oauth chip |
| Статус | active/inactive chip |
| Студент | linked student full_name |
| Остання перевірка | last_validated_at formatted date |
| Дії | "Поточний" (set-current), "Перевірено" (mark-validated), Edit, Delete |

**Add/Edit Account Dialog**:
- `Select` "Студент" (populated from `/api/students`)
- `TextField` "Логін (username)"
- `Select` "Провайдер": GitHub / GitLab / Bitbucket
- `Select` "Тип авторизації": PAT / SSH / OAuth

---

### Page 4: Облікові дані (`/credentials`)

**Toolbar:** "+ Додати" (opens add dialog), "Оновити"

**MUI Table** columns:
| Column | Notes |
|--------|-------|
| Акаунт | linked account username |
| Тип авт. | auth_type chip |
| Секрет (замаскований) | `masked_secret` in monospace font, never show raw |
| Остання перевірка | last_validated_at |
| Дії | "Ротувати 🔄" (opens rotate dialog), Delete 🗑️ |

**Add Credential Dialog**:
- `Select` "Акаунт" (from `/api/accounts`)
- `Select` "Тип авт."
- `TextField` type="password" "Токен / PAT"
- Note: "Секрет зберігається в OS keyring, не в базі даних"

**Rotate Dialog**:
- `TextField` type="password" "Новий PAT/токен"
- Confirm button → PUT `/api/credentials/{id}/rotate`

---

### Page 5: Репозиторії (`/repositories`)

**Toolbar:** "+ Додати репозиторій", "Оновити", "Canonical репо" button

**MUI Table** columns:
| Column | Notes |
|--------|-------|
| Назва репо | derived from URL |
| Локальний шлях | local_path, monospace |
| Remote URL | url, truncated with tooltip |
| Гілка | branch chip |
| Стан синхр. | `Chip`: clean=green, dirty=yellow, diverged=orange, error=red, uninitialized=grey |
| Останній коміт | last_commit_sha (short) + last_commit_msg |
| Дії | "Перевірити" (validate-remote), "Статус" (reload status), Edit |

**Add Repository Dialog**:
- `Select` "Студент"
- `TextField` "Remote URL" (GitHub https URL)
- `TextField` "Гілка" (default: main)
- `TextField` "Локальний шлях" (optional, auto-generated if empty)

**Canonical Repo Panel** (`GET /api/repositories/canonical`):
- Shown in an `Accordion` or side `Drawer`
- Displays: path, branch, last sync, student count

---

### Page 6: Промти (`/prompts`)

Splitter layout (MUI `Grid` 2-column):

**Left: список промтів** (60% width):
`Table` columns: #, Назва, Файл, Статус (colored chip), Відправлено

Status colors:
- `pushed` → green chip
- `committed` → teal chip
- `written` → orange chip
- `draft` → grey chip
- `failed` → red chip + "Повторити" button

Click row → load into right panel

**Right: редактор промту** (40% width):
- `TextField` "Назва промту"
- `TextField` "Шлях до файлу" (e.g., `prompts/task-01.md`)
- `Select` "Студент" (optional — target specific student)
- `TextField` multiline tall "Вміст промту" (markdown text)
- Button row: "Зберегти чернетку" (POST, status=draft), "Відправити в репо" (POST, status=written→pushed)

---

### Page 7: Журнал (`/audit`)

**Toolbar:**
- `Select` "Тип сутності": (all), student, account, credential, repository, sync, handoff, prompt
- `TextField` "Дія" — text filter
- `Button` "Оновити"
- `Button` "Експорт CSV" — downloads as `audit-log.csv`

**MUI Table** columns:
| Timestamp | Actor | Дія | Тип | ID сутності | Деталі |
|-----------|-------|-----|-----|-------------|--------|
| formatted datetime | actor string | action string | entity_type chip | entity_id | details truncated |

Rows: alternating colors, dense (40px row height)

---

### Page 8: Налаштування (`/settings`)

Two sections:

**Секція 1 — API з'єднання** (reads/writes localStorage):
- `TextField` "API URL" (localStorage key: `sf_api_url`, default from `VITE_API_URL`)
- `TextField` type="password" "API Token" (localStorage key: `sf_api_token`)
- `Button` "Зберегти" → saves to localStorage + reloads api client
- `Button` "Перевірити з'єднання" → GET `/api/health`, shows MUI `Alert` with result

**Секція 2 — Налаштування бекенду** (reads/writes `/api/settings`):
- MUI `List` of all key-value settings from `GET /api/settings`
- Each row: key label + editable `TextField` + Save icon button
- `Button` "+ Додати параметр" → inline new row with key+value inputs

**Секція 3 — Про застосунок**:
- Version: 1.0.0
- License: Elastic License 2.0
- GitHub: https://github.com/maxfraieho/Students-flow-API
- "Завантажити десктоп-версію" → GitHub Releases link

---

### SSE Real-time (Dashboard)

```typescript
// src/hooks/useSSE.ts
export function useSSE(onStudent: (s: Student) => void, onStatus: (live: boolean) => void) {
  useEffect(() => {
    const base = import.meta.env.VITE_API_URL || localStorage.getItem('sf_api_url');
    const token = import.meta.env.VITE_API_TOKEN || localStorage.getItem('sf_api_token');
    const es = new EventSource(`${base}/api/sync/broadcast?token=${token}`);
    es.onmessage = e => onStudent(JSON.parse(e.data));
    es.onopen = () => onStatus(true);
    es.onerror = () => onStatus(false);
    return () => es.close();
  }, []);
}
```

---

### MUI Theme

```typescript
createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#1976d2' },
    secondary: { main: '#43a047' },
  },
  components: {
    MuiTableRow: { styleOverrides: { root: { '&:hover': { backgroundColor: '#f5f5f5' } } } },
    MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
  },
})
```

Status → color helper:
```typescript
const STATUS_COLOR: Record<string, ChipProps['color']> = {
  active: 'success', paused: 'warning', exhausted: 'default',
  error: 'error', archived: 'default',
  clean: 'success', dirty: 'warning', diverged: 'warning', uninitialized: 'default',
  pushed: 'success', committed: 'info', written: 'warning', draft: 'default', failed: 'error',
};
```

---

### General Rules
- All UI labels in **Ukrainian**
- No mock data — always fetch from real API
- Loading: MUI `Skeleton` placeholders
- Errors: MUI `Alert` severity="error" with retry `Button`
- Success mutations: MUI `Snackbar` with `Alert` (3s auto-close)
- Use `useQuery` for reads, `useMutation` + `queryClient.invalidateQueries` for writes
- Responsive: mobile drawer toggle, stacked columns on small screens
- Secrets (`TextField` type="password") have a show/hide toggle icon button
