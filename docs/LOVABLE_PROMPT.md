# Lovable Prompt — StudentFlow Frontend

Paste this entire message as the **first prompt** when creating a new Lovable project
(after importing the GitHub repository).

---

## Prompt (paste into Lovable)

Build a complete **StudentFlow** web application. This is a real-time student sync
dashboard for a teacher/operator to manage classroom GitHub sync sessions.

### Tech Stack (already installed)
- React + TypeScript + Vite
- **Material UI (MUI v5)** — use Material Design for ALL components
- Axios for REST API calls
- Native `EventSource` for SSE (Server-Sent Events)

### Environment Variables
```
VITE_API_URL   — Cloudflare Worker base URL (e.g. https://studentflow-api-gateway.maxfraieho.workers.dev)
VITE_API_TOKEN — Bearer token
```

Every API request must include the header:
```
Authorization: Bearer <VITE_API_TOKEN>
```

Create a central `api.ts` file:
```typescript
import axios from 'axios';
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL });
api.interceptors.request.use(cfg => {
  cfg.headers.Authorization = `Bearer ${import.meta.env.VITE_API_TOKEN}`;
  return cfg;
});
export default api;
```

### API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/health | Health check → `{"status":"ok"}` |
| GET | /api/students | All students array |
| GET | /api/students/active | Current active student |
| GET | /api/students/next | Next in queue |
| POST | /api/students/{id}/activate | Activate a student |
| GET | /api/sync/broadcast?token=TOKEN | SSE stream — emits active student JSON |

---

### Page 1: Landing Page (`/`)

Full-page landing with MUI components:

**AppBar**: "StudentFlow" logo + "Dashboard" link + "GitHub" icon button

**Hero Section**:
- Large `Typography` h1: "Синхронізація студентів у реальному часі"
- Subtitle: "Автоматична синхронізація GitHub репозиторіїв вашого класу"
- Two CTA buttons: "Розпочати безкоштовно" (outlined) and "Переглянути демо" (contained)

**Pricing Section** — two MUI `Card` components side by side:

Card 1 — **Безкоштовно** (outlined, grey border):
- Price: **0 ₴ / місяць**
- Features list with `CheckCircle` icons:
  - ✓ До 50 синхронізацій на місяць
  - ✓ 1 клас
  - ✓ Базова панель
  - ✗ SSE real-time оновлення
  - ✗ Пріоритетна підтримка
- Button: "Розпочати" (outlined)

Card 2 — **Pro** (elevated, primary color `#1976d2` header):
- Price: **150 ₴ / місяць** or **1200 ₴ / рік**
- Badge: `Chip` "Найпопулярніший" in secondary color
- Features list:
  - ✓ Необмежені синхронізації
  - ✓ Необмежена кількість класів
  - ✓ SSE real-time оновлення
  - ✓ Пріоритетна підтримка
  - ✓ Експорт звітів
- Button: "Отримати Pro" (contained, primary)

**Download Section**:
- `Paper` with slight elevation
- Icon: `Download`
- Title: "Завантажити застосунок StudentFlow"
- Subtitle: "Десктоп-версія для офлайн управління синхронізацією"
- Button: "Завантажити для Windows / Linux" → links to GitHub Releases page
- Small text: "Безкоштовно • Open Source"

**Open Source Section**:
- GitHub icon + "Вихідний код"
- "Переглянути на GitHub" button → links to `https://github.com/maxfraieho/Students-flow-API`
- `Chip` with label: "Elastic License 2.0"
- Small text: "Самостійне розгортання дозволено. Комерційний SaaS — ні."

**Footer**: copyright + links

---

### Page 2: Dashboard (`/dashboard`)

Layout: MUI `AppBar` + left `Drawer` (240px) + main content

**AppBar** contains:
- "StudentFlow" title
- Right side: SSE status `Chip` — green pulsing dot + "Онлайн" when connected, grey "Офлайн" when disconnected
- Avatar icon button (placeholder)

**Left Drawer** navigation:
- `List` items: Панель, Студенти, Налаштування
- Icons: `Dashboard`, `People`, `Settings`

**Main Content — three sections:**

**Section 1: Активний студент** (top, full width):
MUI `Card` with primary colored `CardHeader`:
- Large `Typography` with student full_name
- `Chip` "Активний" in green
- `Avatar` with student initials (large, 80px)
- Two action buttons:
  - "Наступний студент" `Button` (contained, calls POST /api/students/{next_id}/activate)
  - "Деталі" `Button` (outlined)
- If no active student: `Alert` severity="info" "Немає активного студента"

**Section 2: Черга студентів** (left column, 60% width):
MUI `List` — each item shows:
- `Avatar` with initials + queue position number badge
- Primary text: full_name
- Secondary text: status chip
- Right: `IconButton` to activate

**Section 3: Статистика** (right column, 40% width):
Three MUI `Paper` stat cards:
- Всього студентів: count
- Активних: count  
- Синхронізацій сьогодні: (mock: 0 for free users)

**Free tier sync counter** (bottom of page):
- `LinearProgress` bar
- Text: "Використано 32 / 50 синхронізацій цього місяця"
- `Button` "Перейти на Pro" next to it

---

### Page 3: Settings (`/settings`)

MUI `Paper` form:
- `TextField` "API URL" (reads/writes localStorage key `sf_api_url`)
- `TextField` type="password" "API Token" (reads/writes localStorage key `sf_api_token`)
- `Button` "Зберегти" — saves to localStorage
- `Button` "Перевірити з'єднання" — calls GET /api/health and shows MUI `Alert` with result
- `Divider`
- `Typography` "Версія: 1.0.0 • Ліцензія: Elastic License 2.0"

---

### SSE Real-time Updates

In the Dashboard, connect to SSE for live updates:
```typescript
useEffect(() => {
  const token = import.meta.env.VITE_API_TOKEN;
  const url = `${import.meta.env.VITE_API_URL}/api/sync/broadcast?token=${token}`;
  const es = new EventSource(url);
  es.onmessage = (e) => {
    const student = JSON.parse(e.data);
    setActiveStudent(student);
  };
  es.onopen = () => setLive(true);
  es.onerror = () => setLive(false);
  return () => es.close();
}, []);
```

---

### Design Rules
- Use `createTheme({ palette: { primary: { main: '#1976d2' }, secondary: { main: '#43a047' } } })`
- All UI text in Ukrainian
- Loading states: use MUI `Skeleton`
- Error states: use MUI `Alert` with retry `Button`
- Mobile-first responsive design using MUI `Grid` and `useMediaQuery`
- No mock/hardcoded student data — always fetch from API
