import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  AppBar,
  Avatar,
  Badge,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Divider,
  Drawer,
  Grid,
  IconButton,
  LinearProgress,
  List,
  ListItem,
  ListItemAvatar,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Skeleton,
  Stack,
  TextField,
  Toolbar,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import DashboardIcon from "@mui/icons-material/Dashboard";
import PeopleIcon from "@mui/icons-material/People";
import SettingsIcon from "@mui/icons-material/Settings";
import GitHubIcon from "@mui/icons-material/GitHub";
import DownloadIcon from "@mui/icons-material/Download";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RefreshIcon from "@mui/icons-material/Refresh";
import {
  activateStudent,
  getActiveStudent,
  getBroadcastUrl,
  getHealth,
  getNextStudent,
  getRuntimeConfig,
  getStudents,
  saveRuntimeConfig,
} from "./api";
import type { Student } from "./types";

type RoutePath = "/" | "/dashboard" | "/settings";

const drawerWidth = 240;
const navItems: Array<{ path: RoutePath; label: string }> = [
  { path: "/", label: "Головна" },
  { path: "/dashboard", label: "Дашборд" },
  { path: "/settings", label: "Налаштування" },
];

const dashboardDrawerItems = [
  { label: "Панель", icon: <DashboardIcon />, action: "dashboard" },
  { label: "Студенти", icon: <PeopleIcon />, action: "students" },
  { label: "Налаштування", icon: <SettingsIcon />, action: "settings" },
] as const;

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

function getStudentName(student: Student | null | undefined) {
  if (!student) return "Немає активного студента";
  return student.full_name || student.github_login || student.id;
}

function getStudentInitials(student: Student | null | undefined) {
  if (!student) return "--";
  const fullName = student.full_name || student.github_login || "";
  const parts = fullName.trim().split(" ").filter(Boolean);
  if (parts.length === 0) return student.id.slice(0, 2).toUpperCase();
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function LandingPage({ go }: { go: (path: RoutePath) => void }) {
  return (
    <Box>
      <AppBar position="sticky" color="inherit" elevation={0}>
        <Toolbar sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
            StudentFlow
          </Typography>
          <Button onClick={() => go("/dashboard")}>Дашборд</Button>
          <IconButton
            component="a"
            href="https://github.com/maxfraieho/Students-flow-API"
            target="_blank"
            rel="noreferrer"
            aria-label="GitHub"
          >
            <GitHubIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Box component="main" sx={{ maxWidth: 1200, mx: "auto", px: 3, py: 6 }}>
        <Stack spacing={7}>
          <Stack spacing={2}>
            <Typography variant="h2" component="h1" sx={{ fontWeight: 800, maxWidth: 900 }}>
              Синхронізація студентів у реальному часі
            </Typography>
            <Typography variant="h5" color="text.secondary" sx={{ maxWidth: 760 }}>
              Автоматична синхронізація GitHub репозиторіїв вашого класу
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ pt: 1 }}>
              <Button variant="outlined" size="large" onClick={() => go("/settings")}>
                Розпочати безкоштовно
              </Button>
              <Button variant="contained" size="large" onClick={() => go("/dashboard")}>
                Переглянути демо
              </Button>
            </Stack>
          </Stack>

          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card variant="outlined" sx={{ height: "100%" }}>
                <CardContent>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    Безкоштовно
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 800, mt: 2 }}>
                    0 ₴ / місяць
                  </Typography>
                  <Stack spacing={1.5} sx={{ mt: 3 }}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <CheckCircleIcon color="secondary" fontSize="small" />
                      <Typography>До 50 синхронізацій на місяць</Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <CheckCircleIcon color="secondary" fontSize="small" />
                      <Typography>1 клас</Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <CheckCircleIcon color="secondary" fontSize="small" />
                      <Typography>Базова панель</Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <CancelIcon color="disabled" fontSize="small" />
                      <Typography color="text.secondary">SSE real-time оновлення</Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <CancelIcon color="disabled" fontSize="small" />
                      <Typography color="text.secondary">Пріоритетна підтримка</Typography>
                    </Stack>
                  </Stack>
                  <Button variant="outlined" sx={{ mt: 3 }} onClick={() => go("/settings")}>
                    Розпочати
                  </Button>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ height: "100%" }}>
                <Box sx={{ bgcolor: "primary.main", color: "primary.contrastText", p: 2.5 }}>
                  <Stack direction="row" alignItems="center" justifyContent="space-between">
                    <Typography variant="h5" sx={{ fontWeight: 700 }}>
                      Pro
                    </Typography>
                    <Chip label="Найпопулярніший" color="secondary" />
                  </Stack>
                </Box>
                <CardContent>
                  <Typography variant="h4" sx={{ fontWeight: 800 }}>
                    150 ₴ / місяць
                  </Typography>
                  <Typography color="text.secondary">або 1200 ₴ / рік</Typography>
                  <Stack spacing={1.5} sx={{ mt: 3 }}>
                    {[
                      "Необмежені синхронізації",
                      "Необмежена кількість класів",
                      "SSE real-time оновлення",
                      "Пріоритетна підтримка",
                      "Експорт звітів",
                    ].map((item) => (
                      <Stack direction="row" spacing={1} alignItems="center" key={item}>
                        <CheckCircleIcon color="secondary" fontSize="small" />
                        <Typography>{item}</Typography>
                      </Stack>
                    ))}
                  </Stack>
                  <Button variant="contained" sx={{ mt: 3 }} onClick={() => go("/settings")}>
                    Отримати Pro
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Paper elevation={2} sx={{ p: 3.5 }}>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ xs: "flex-start", md: "center" }}>
              <DownloadIcon color="primary" />
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  Завантажити застосунок StudentFlow
                </Typography>
                <Typography color="text.secondary">
                  Десктоп-версія для офлайн управління синхронізацією
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Безкоштовно • Open Source
                </Typography>
              </Box>
              <Button
                variant="contained"
                component="a"
                href="https://github.com/maxfraieho/Students-flow-API/releases"
                target="_blank"
                rel="noreferrer"
              >
                Завантажити для Windows / Linux
              </Button>
            </Stack>
          </Paper>

          <Paper variant="outlined" sx={{ p: 3.5 }}>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ xs: "flex-start", md: "center" }}>
              <GitHubIcon color="action" />
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  Вихідний код
                </Typography>
                <Typography color="text.secondary">
                  Самостійне розгортання дозволено. Комерційний SaaS — ні.
                </Typography>
              </Box>
              <Chip label="Elastic License 2.0" variant="outlined" />
              <Button
                variant="outlined"
                component="a"
                href="https://github.com/maxfraieho/Students-flow-API"
                target="_blank"
                rel="noreferrer"
              >
                Переглянути на GitHub
              </Button>
            </Stack>
          </Paper>
        </Stack>
      </Box>

      <Box component="footer" sx={{ borderTop: 1, borderColor: "divider", py: 3, px: 3 }}>
        <Stack
          sx={{ maxWidth: 1200, mx: "auto" }}
          direction={{ xs: "column", md: "row" }}
          alignItems={{ xs: "flex-start", md: "center" }}
          justifyContent="space-between"
          spacing={1}
        >
          <Typography variant="body2" color="text.secondary">
            © {new Date().getFullYear()} StudentFlow
          </Typography>
          <Stack direction="row" spacing={2}>
            <Button size="small" onClick={() => go("/dashboard")}>
              Dashboard
            </Button>
            <Button
              size="small"
              component="a"
              href="https://github.com/maxfraieho/Students-flow-API"
              target="_blank"
              rel="noreferrer"
            >
              GitHub
            </Button>
          </Stack>
        </Stack>
      </Box>
    </Box>
  );
}

function DashboardPage({ go }: { go: (path: RoutePath) => void }) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [students, setStudents] = useState<Student[]>([]);
  const [activeStudent, setActiveStudent] = useState<Student | null>(null);
  const [live, setLive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      const [studentsData, active] = await Promise.all([getStudents(), getActiveStudent()]);
      setStudents(studentsData);
      setActiveStudent(active);
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : "Невідома помилка";
      setError(`Не вдалося завантажити дані: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  useEffect(() => {
    const es = new EventSource(getBroadcastUrl());

    es.onmessage = (event) => {
      try {
        const payload: unknown = JSON.parse(event.data);

        if (
          typeof payload === "object" &&
          payload !== null &&
          "active_student" in payload
        ) {
          const next = (payload as { active_student?: Student | null }).active_student;
          setActiveStudent(next ?? null);
          return;
        }

        if (
          typeof payload === "object" &&
          payload !== null &&
          "id" in payload
        ) {
          setActiveStudent(payload as Student);
        }
      } catch {
        // ignore parse errors from invalid SSE payloads
      }
    };

    es.onopen = () => setLive(true);
    es.onerror = () => setLive(false);

    return () => es.close();
  }, []);

  const queue = useMemo(
    () => students.filter((student) => student.id !== activeStudent?.id),
    [students, activeStudent?.id],
  );

  const syncCountToday = 0;
  const freeLimit = 50;
  const usedSync = Math.min(syncCountToday, freeLimit);
  const progress = Math.round((usedSync / freeLimit) * 100);

  const handleActivateStudent = async (studentId: string) => {
    setActionLoading(true);
    try {
      await activateStudent(studentId);
      await loadData();
    } catch (activateError) {
      const message = activateError instanceof Error ? activateError.message : "Невідома помилка";
      setError(`Не вдалося активувати студента: ${message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleActivateNext = async () => {
    setActionLoading(true);
    try {
      const nextStudent = await getNextStudent();
      if (!nextStudent) {
        setError("Черга порожня — наступного студента немає.");
        return;
      }

      await activateStudent(nextStudent.id);
      await loadData();
    } catch (nextError) {
      const message = nextError instanceof Error ? nextError.message : "Невідома помилка";
      setError(`Не вдалося активувати наступного студента: ${message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const drawer = (
    <Box sx={{ width: drawerWidth }}>
      <Toolbar />
      <Divider />
      <List>
        {dashboardDrawerItems.map((item) => (
          <ListItem key={item.label} disablePadding>
            <ListItemButton
              onClick={() => {
                if (item.action === "settings") {
                  go("/settings");
                } else if (item.action === "students") {
                  document.getElementById("students-section")?.scrollIntoView({ behavior: "smooth" });
                } else {
                  document.getElementById("dashboard-section")?.scrollIntoView({ behavior: "smooth" });
                }
                if (isMobile) setDrawerOpen(false);
              }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
        <Toolbar>
          {isMobile && (
            <IconButton color="inherit" edge="start" sx={{ mr: 2 }} onClick={() => setDrawerOpen(true)}>
              <MenuIcon />
            </IconButton>
          )}
          <Typography variant="h6" sx={{ fontWeight: 700, flexGrow: 1 }}>
            StudentFlow
          </Typography>

          <Chip
            label={live ? "Онлайн" : "Офлайн"}
            color={live ? "secondary" : "default"}
            sx={{ mr: 2 }}
            icon={
              <Badge
                variant="dot"
                color={live ? "success" : "default"}
                sx={{
                  "& .MuiBadge-badge": {
                    animation: live ? "pulse 1.4s infinite" : "none",
                    "@keyframes pulse": {
                      "0%": { transform: "scale(1)", opacity: 1 },
                      "70%": { transform: "scale(1.8)", opacity: 0.2 },
                      "100%": { transform: "scale(1)", opacity: 1 },
                    },
                  },
                }}
              >
                <Box sx={{ width: 8, height: 8 }} />
              </Badge>
            }
          />

          <IconButton color="inherit">
            <Avatar sx={{ width: 30, height: 30 }}>U</Avatar>
          </IconButton>
        </Toolbar>
      </AppBar>

      {isMobile ? (
        <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)}>
          {drawer}
        </Drawer>
      ) : (
        <Drawer variant="permanent" sx={{
          width: drawerWidth,
          flexShrink: 0,
          "& .MuiDrawer-paper": { width: drawerWidth, boxSizing: "border-box" },
        }}>
          {drawer}
        </Drawer>
      )}

      <Box component="main" sx={{ flexGrow: 1, p: { xs: 2, md: 4 }, mt: 8 }}>
        <Stack spacing={3}>
          {error && (
            <Alert
              severity="error"
              action={
                <Button color="inherit" size="small" startIcon={<RefreshIcon />} onClick={() => void loadData()}>
                  Повторити
                </Button>
              }
            >
              {error}
            </Alert>
          )}

          <Card id="dashboard-section">
            <CardHeader
              title="Активний студент"
              sx={{ bgcolor: "primary.main", color: "primary.contrastText" }}
            />
            <CardContent>
              {loading ? (
                <Stack spacing={2}>
                  <Skeleton variant="text" width="40%" height={48} />
                  <Skeleton variant="rectangular" width="100%" height={120} />
                </Stack>
              ) : activeStudent ? (
                <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" alignItems={{ xs: "flex-start", md: "center" }} spacing={2}>
                  <Stack spacing={1.5}>
                    <Typography variant="h4" sx={{ fontWeight: 700 }}>
                      {getStudentName(activeStudent)}
                    </Typography>
                    <Chip label="Активний" color="success" sx={{ width: "fit-content" }} />
                    <Stack direction="row" spacing={1.5}>
                      <Button
                        variant="contained"
                        startIcon={<PlayArrowIcon />}
                        onClick={() => void handleActivateNext()}
                        disabled={actionLoading}
                      >
                        Наступний студент
                      </Button>
                      <Button variant="outlined">Деталі</Button>
                    </Stack>
                  </Stack>
                  <Avatar sx={{ width: 80, height: 80, fontSize: 28 }}>
                    {getStudentInitials(activeStudent)}
                  </Avatar>
                </Stack>
              ) : (
                <Alert severity="info">Немає активного студента</Alert>
              )}
            </CardContent>
          </Card>

          <Grid container spacing={3}>
            <Grid size={{ xs: 12, lg: 7 }} id="students-section">
              <Paper variant="outlined" sx={{ p: 2.5 }}>
                <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>
                  Черга студентів
                </Typography>

                {loading ? (
                  <Stack spacing={1.5}>
                    {Array.from({ length: 4 }).map((_, index) => (
                      <Skeleton key={index} variant="rectangular" height={58} />
                    ))}
                  </Stack>
                ) : queue.length === 0 ? (
                  <Alert severity="info">Черга порожня</Alert>
                ) : (
                  <List disablePadding>
                    {queue.map((student, index) => (
                      <ListItem
                        key={student.id}
                        divider
                        secondaryAction={
                          <IconButton
                            edge="end"
                            color="primary"
                            disabled={actionLoading}
                            onClick={() => void handleActivateStudent(student.id)}
                          >
                            <PlayArrowIcon />
                          </IconButton>
                        }
                      >
                        <ListItemAvatar>
                          <Badge badgeContent={`#${index + 1}`} color="primary">
                            <Avatar>{getStudentInitials(student)}</Avatar>
                          </Badge>
                        </ListItemAvatar>
                        <ListItemText
                          primary={getStudentName(student)}
                          secondary={
                            <Chip
                              label={student.status || "У черзі"}
                              size="small"
                              variant="outlined"
                              sx={{ mt: 0.5 }}
                            />
                          }
                        />
                      </ListItem>
                    ))}
                  </List>
                )}
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, lg: 5 }}>
              <Stack spacing={2}>
                <Paper variant="outlined" sx={{ p: 2.5 }}>
                  <Typography color="text.secondary">Всього студентів</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    {loading ? <Skeleton width={80} /> : students.length}
                  </Typography>
                </Paper>
                <Paper variant="outlined" sx={{ p: 2.5 }}>
                  <Typography color="text.secondary">Активних</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    {loading ? <Skeleton width={80} /> : activeStudent ? 1 : 0}
                  </Typography>
                </Paper>
                <Paper variant="outlined" sx={{ p: 2.5 }}>
                  <Typography color="text.secondary">Синхронізацій сьогодні</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    {loading ? <Skeleton width={80} /> : syncCountToday}
                  </Typography>
                </Paper>
              </Stack>
            </Grid>
          </Grid>

          <Paper variant="outlined" sx={{ p: 2.5 }}>
            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={2}
              alignItems={{ xs: "flex-start", md: "center" }}
              justifyContent="space-between"
            >
              <Box sx={{ width: "100%" }}>
                <Typography sx={{ mb: 1 }}>
                  Використано {usedSync} / {freeLimit} синхронізацій цього місяця
                </Typography>
                <LinearProgress variant="determinate" value={progress} />
              </Box>
              <Button variant="contained" onClick={() => go("/")}>Перейти на Pro</Button>
            </Stack>
          </Paper>
        </Stack>
      </Box>
    </Box>
  );
}

function SettingsPage() {
  const runtime = getRuntimeConfig();
  const [apiUrl, setApiUrl] = useState(runtime.apiUrl);
  const [apiToken, setApiToken] = useState(runtime.apiToken);
  const [checking, setChecking] = useState(false);
  const [status, setStatus] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleSave = () => {
    saveRuntimeConfig(apiUrl, apiToken);
    setStatus({ type: "success", text: "Налаштування збережено" });
  };

  const handleCheck = async () => {
    setChecking(true);
    setStatus(null);

    try {
      saveRuntimeConfig(apiUrl, apiToken);
      const health = await getHealth();
      const ok = health.status === "ok" || health.healthy === true;

      if (ok) {
        setStatus({ type: "success", text: "З'єднання успішне" });
      } else {
        setStatus({ type: "error", text: "Сервер відповів з помилкою" });
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Невідома помилка";
      setStatus({ type: "error", text: `Помилка з'єднання: ${message}` });
    } finally {
      setChecking(false);
    }
  };

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default", py: 8, px: 2 }}>
      <Paper sx={{ maxWidth: 780, mx: "auto", p: { xs: 3, md: 4 } }}>
        <Typography variant="h2" component="h1" sx={{ mb: 4, fontWeight: 800 }}>
          Налаштування
        </Typography>

        <Stack spacing={3}>
          <TextField
            label="API URL"
            value={apiUrl}
            onChange={(event) => setApiUrl(event.target.value)}
            fullWidth
          />

          <TextField
            label="API Token"
            value={apiToken}
            onChange={(event) => setApiToken(event.target.value)}
            type="password"
            fullWidth
          />

          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <Button variant="contained" onClick={handleSave}>
              Зберегти
            </Button>
            <Button variant="outlined" onClick={() => void handleCheck()} disabled={checking}>
              Перевірити з'єднання
            </Button>
          </Stack>

          {status && <Alert severity={status.type}>{status.text}</Alert>}

          <Divider />

          <Typography color="text.secondary">Версія: 1.0.0 • Ліцензія: Elastic License 2.0</Typography>
        </Stack>
      </Paper>
    </Box>
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

  if (route === "/") return <LandingPage go={go} />;
  if (route === "/dashboard") return <DashboardPage go={go} />;
  return <SettingsPage />;
}

export default App;
