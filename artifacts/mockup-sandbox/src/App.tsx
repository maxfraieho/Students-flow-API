import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  AppBar,
  Avatar,
  Badge,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Drawer,
  FormControl,
  IconButton,
  InputAdornment,
  InputLabel,
  LinearProgress,
  List,
  ListItem,
  ListItemAvatar,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Skeleton,
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import DashboardIcon from "@mui/icons-material/Dashboard";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import FolderSpecialIcon from "@mui/icons-material/FolderSpecial";
import HistoryIcon from "@mui/icons-material/History";
import KeyIcon from "@mui/icons-material/Key";
import ManageAccountsIcon from "@mui/icons-material/ManageAccounts";
import MenuIcon from "@mui/icons-material/Menu";
import PeopleIcon from "@mui/icons-material/People";
import PsychologyIcon from "@mui/icons-material/Psychology";
import SettingsIcon from "@mui/icons-material/Settings";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import SaveIcon from "@mui/icons-material/Save";
import RefreshIcon from "@mui/icons-material/Refresh";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import CloudDoneIcon from "@mui/icons-material/CloudDone";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import AddIcon from "@mui/icons-material/Add";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import LaunchIcon from "@mui/icons-material/Launch";
import type {
  Account,
  AuditItem,
  Credential,
  PromptItem,
  Repository,
  SettingItem,
  Student,
  SyncJob,
} from "./types";
import {
  activateStudent,
  archiveStudent,
  bulkImportStudents,
  checkCredentialExists,
  createAccount,
  createCredential,
  createPrompt,
  createRepository,
  createStudent,
  deleteAccount,
  deleteBackendSetting,
  deleteCredential,
  fetchAccounts,
  fetchActiveStudent,
  fetchAudit,
  fetchBackendSettings,
  fetchCanonicalRepository,
  fetchCredentials,
  fetchNextStudent,
  fetchPromptById,
  fetchPrompts,
  fetchRepositories,
  fetchRepositoryStatus,
  fetchStudents,
  fetchSyncJobs,
  getRuntimeConfig,
  healthCheck,
  markValidated,
  putBackendSetting,
  retryPrompt,
  rotateCredential,
  saveRuntimeConfig,
  setCurrentAccount,
  syncCurrentStudent,
  syncSpecificStudent,
  syncStudentToCanonical,
  triggerHandoff,
  updateAccount,
  updateRepository,
  updateStudent,
  validateRepositoryRemote,
} from "./api/client";
import { useSSE } from "./hooks/useSSE";

const drawerWidth = 240;

type ToastState = {
  open: boolean;
  message: string;
  severity: "success" | "error";
};

const STATUS_COLOR: Record<string, "success" | "warning" | "default" | "error" | "info"> = {
  active: "success",
  paused: "warning",
  exhausted: "default",
  error: "error",
  archived: "default",
  clean: "success",
  dirty: "warning",
  diverged: "warning",
  uninitialized: "default",
  pushed: "success",
  committed: "info",
  written: "warning",
  draft: "default",
  failed: "error",
};

const NAV_ITEMS = [
  { path: "/dashboard", label: "Dashboard", icon: <DashboardIcon /> },
  { path: "/students", label: "Студенти", icon: <PeopleIcon /> },
  { path: "/accounts", label: "Акаунти", icon: <ManageAccountsIcon /> },
  { path: "/credentials", label: "Облікові дані", icon: <KeyIcon /> },
  { path: "/repositories", label: "Репозиторії", icon: <FolderSpecialIcon /> },
  { path: "/prompts", label: "Промти", icon: <PsychologyIcon /> },
  { path: "/audit", label: "Журнал", icon: <HistoryIcon /> },
] as const;

function useToast() {
  const [toast, setToast] = useState<ToastState>({
    open: false,
    message: "",
    severity: "success",
  });

  const showToast = useCallback((message: string, severity: "success" | "error" = "success") => {
    setToast({ open: true, message, severity });
  }, []);

  return { toast, setToast, showToast };
}

function ActionSnackbar({
  toast,
  onClose,
}: {
  toast: ToastState;
  onClose: () => void;
}) {
  return (
    <Snackbar
      open={toast.open}
      autoHideDuration={3000}
      onClose={onClose}
      anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
    >
      <Alert severity={toast.severity} onClose={onClose} variant="filled">
        {toast.message}
      </Alert>
    </Snackbar>
  );
}

function initials(name?: string | null) {
  if (!name) return "--";
  const parts = name.trim().split(" ").filter(Boolean);
  if (!parts.length) return "--";
  return parts.slice(0, 2).map((part) => part[0]?.toUpperCase()).join("");
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("uk-UA", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function statusChip(status?: string) {
  return <Chip size="small" color={STATUS_COLOR[status || ""] || "default"} label={status || "—"} />;
}

function LiveChip({ live }: { live: boolean }) {
  return (
    <Chip
      label={live ? "Онлайн" : "Офлайн"}
      color={live ? "success" : "default"}
      icon={
        <Badge variant="dot" color={live ? "success" : "default"} sx={{ "& .MuiBadge-badge": { right: -2, top: 11 } }}>
          <Box sx={{ width: 10, height: 10 }} />
        </Badge>
      }
    />
  );
}

function LoadingState() {
  return (
    <Stack spacing={1.5}>
      <Skeleton variant="rounded" height={56} />
      <Skeleton variant="rounded" height={56} />
      <Skeleton variant="rounded" height={56} />
    </Stack>
  );
}

function DashboardPage({ setLive }: { setLive: (v: boolean) => void }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [sseStudent, setSseStudent] = useState<Student | null>(null);
  const [stableActiveStudent, setStableActiveStudent] = useState<Student | null>(null);
  const { toast, setToast, showToast } = useToast();

  const studentsQuery = useQuery({ queryKey: ["students"], queryFn: () => fetchStudents() });
  const activeQuery = useQuery({ queryKey: ["students", "active"], queryFn: fetchActiveStudent });
  const nextQuery = useQuery({ queryKey: ["students", "next"], queryFn: fetchNextStudent });
  const jobsQuery = useQuery({ queryKey: ["sync", "jobs"], queryFn: fetchSyncJobs, refetchInterval: 15000 });
  const canonicalQuery = useQuery({ queryKey: ["repositories", "canonical"], queryFn: fetchCanonicalRepository });

  useSSE(
    useCallback((student) => setSseStudent(student), []),
    useCallback(
      (live) => {
        setLive(live);
      },
      [setLive],
    ),
  );

  useEffect(() => {
    if (sseStudent) {
      setStableActiveStudent(sseStudent);
      return;
    }

    if (activeQuery.data) {
      setStableActiveStudent(activeQuery.data);
      return;
    }

    if (activeQuery.isFetched && !activeQuery.isFetching) {
      const clearId = window.setTimeout(() => setStableActiveStudent(null), 1500);
      return () => window.clearTimeout(clearId);
    }
  }, [sseStudent, activeQuery.data, activeQuery.isFetched, activeQuery.isFetching]);

  const syncCurrentMutation = useMutation({
    mutationFn: syncCurrentStudent,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["sync", "jobs"] }),
        queryClient.invalidateQueries({ queryKey: ["students", "active"] }),
      ]);
      showToast("Синхронізацію запущено");
    },
    onError: () => showToast("Не вдалося запустити синхронізацію", "error"),
  });

  const handoffMutation = useMutation({
    mutationFn: triggerHandoff,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["students"] }),
        queryClient.invalidateQueries({ queryKey: ["students", "active"] }),
        queryClient.invalidateQueries({ queryKey: ["sync", "jobs"] }),
      ]);
      showToast("Передачу виконано");
    },
    onError: () => showToast("Не вдалося виконати передачу", "error"),
  });

  const quickSyncMutation = useMutation({
    mutationFn: syncSpecificStudent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sync", "jobs"] });
      showToast("Синхронізацію студента запущено");
    },
    onError: () => showToast("Помилка запуску синхронізації", "error"),
  });

  const activeStudent = sseStudent ?? activeQuery.data ?? stableActiveStudent ?? null;
  const isLoadingActiveStudent = !activeStudent && !activeQuery.isFetched;
  const queue = useMemo(
    () =>
      (studentsQuery.data || [])
        .filter((student) => student.status !== "archived")
        .sort((a, b) => (a.queue_position || 0) - (b.queue_position || 0)),
    [studentsQuery.data],
  );

  const activeError = studentsQuery.error || activeQuery.error || jobsQuery.error;

  return (
    <Stack spacing={2.5}>
      {activeError && (
        <Alert
          severity="error"
          action={<Button onClick={() => void Promise.all([studentsQuery.refetch(), activeQuery.refetch(), jobsQuery.refetch()])}>Повторити</Button>}
        >
          Помилка завантаження дашборду
        </Alert>
      )}

      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "3fr 1fr" } }}>
        <Stack spacing={2}>
          <Paper sx={{ p: 2.5 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
              Активний студент
            </Typography>

            {isLoadingActiveStudent ? (
              <LoadingState />
            ) : !activeStudent ? (
              <Alert severity="info">Немає активного студента</Alert>
            ) : (
              <Stack spacing={2}>
                <Stack direction="row" spacing={2} alignItems="center">
                  <Avatar sx={{ width: 80, height: 80 }}>{initials(activeStudent.full_name)}</Avatar>
                  <Box>
                    <Typography variant="h5" sx={{ fontWeight: 700 }}>
                      {activeStudent.full_name}
                    </Typography>
                    {statusChip(activeStudent.status)}
                  </Box>
                </Stack>

                <Typography variant="body2">Email: {activeStudent.email || "—"}</Typography>
                <Typography variant="body2">Позиція черги: {activeStudent.queue_position ?? "—"}</Typography>
                <Typography variant="body2">Нотатки: {activeStudent.notes || "—"}</Typography>

                <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                  <Button
                    variant="contained"
                    onClick={() => syncCurrentMutation.mutate()}
                    disabled={syncCurrentMutation.isPending}
                  >
                    Синхронізувати
                  </Button>
                  <Button
                    variant="contained"
                    color="secondary"
                    onClick={() => handoffMutation.mutate()}
                    disabled={handoffMutation.isPending}
                  >
                    Наступний студент
                  </Button>
                  <Button variant="outlined" onClick={() => navigate("/students")}>Деталі</Button>
                </Stack>
              </Stack>
            )}
          </Paper>

          <Paper sx={{ p: 2.5 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
              Остання активність
            </Typography>
            {jobsQuery.isLoading ? (
              <LoadingState />
            ) : (
              <List dense>
                {(jobsQuery.data || []).map((job: SyncJob) => (
                  <ListItem
                    key={job.id}
                    secondaryAction={
                      <Chip size="small" label={job.status || "—"} color={job.status === "failed" ? "error" : "default"} />
                    }
                  >
                    <ListItemIcon>
                      {job.status === "success" ? (
                        <CheckCircleIcon color="success" />
                      ) : job.status === "failed" ? (
                        <ErrorIcon color="error" />
                      ) : (
                        <AutorenewIcon color="warning" />
                      )}
                    </ListItemIcon>
                    <ListItemText
                      primary={job.summary || "Синхронізація"}
                      secondary={formatDate(job.finished_at || job.created_at)}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Stack>

        <Stack spacing={2}>
          <Paper sx={{ p: 2.5 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
              Черга
            </Typography>
            {studentsQuery.isLoading ? (
              <LoadingState />
            ) : (
              <List dense>
                {queue.map((student, index) => (
                  <ListItem
                    key={student.id}
                    disablePadding
                    secondaryAction={
                      <IconButton onClick={() => quickSyncMutation.mutate(student.id)} aria-label="sync-student">
                        <CloudDoneIcon />
                      </IconButton>
                    }
                  >
                    <ListItemButton onClick={() => navigate("/students")}>
                      <ListItemAvatar>
                        <Avatar>{initials(student.full_name)}</Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={`${index + 1}. ${student.full_name}`}
                        secondary={student.status || "—"}
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>

          <Paper sx={{ p: 2.5 }}>
            <Typography variant="h6" sx={{ mb: 1, fontWeight: 700 }}>
              Канонічне репо
            </Typography>
            {canonicalQuery.isLoading ? (
              <CircularProgress size={18} />
            ) : canonicalQuery.data ? (
              <Stack spacing={1}>
                <Typography variant="body2">Шлях: {canonicalQuery.data.local_path || "—"}</Typography>
                <Typography variant="body2">
                  Гілка: {canonicalQuery.data.branch || canonicalQuery.data.default_branch || "—"}
                </Typography>
                <Typography variant="body2">Останнє оновлення: {formatDate(canonicalQuery.data.updated_at)}</Typography>
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Канонічне репо не налаштоване
              </Typography>
            )}
          </Paper>
        </Stack>
      </Box>

      <ActionSnackbar toast={toast} onClose={() => setToast((t) => ({ ...t, open: false }))} />
    </Stack>
  );
}

function StudentsPage() {
  const queryClient = useQueryClient();
  const { toast, setToast, showToast } = useToast();
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [editing, setEditing] = useState<Student | null>(null);
  const [bulkPayload, setBulkPayload] = useState("[]");
  const [bulkResult, setBulkResult] = useState<string>("");
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    notes: "",
    queue_position: "",
  });

  const studentsQuery = useQuery({ queryKey: ["students"], queryFn: () => fetchStudents() });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editing) {
        return updateStudent({
          id: editing.id,
          full_name: form.full_name,
          email: form.email || undefined,
          notes: form.notes || undefined,
          queue_position: form.queue_position ? Number(form.queue_position) : undefined,
        });
      }

      return createStudent({
        full_name: form.full_name,
        email: form.email || undefined,
        notes: form.notes || undefined,
        queue_position: form.queue_position ? Number(form.queue_position) : undefined,
      });
    },
    onSuccess: async () => {
      setDialogOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["students"] });
      showToast("Студента збережено");
    },
    onError: () => showToast("Не вдалося зберегти студента", "error"),
  });

  const activateMutation = useMutation({
    mutationFn: async (studentId: string) => {
      try {
        await activateStudent(studentId);
      } catch (error) {
        if (!(axios.isAxiosError(error) && error.response?.status === 409)) {
          throw error;
        }

        const activeFromList = (studentsQuery.data || []).find(
          (student) => student.status === "active" && student.id !== studentId,
        );

        const activeStudent = activeFromList || (await fetchActiveStudent());
        if (activeStudent?.id && activeStudent.id !== studentId) {
          await updateStudent({ id: activeStudent.id, status: "paused" });
        }

        await activateStudent(studentId);
      }
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["students"] }),
        queryClient.invalidateQueries({ queryKey: ["students", "active"] }),
      ]);
      showToast("Студента активовано");
    },
    onError: (error) => {
      const detail = axios.isAxiosError(error)
        ? (error.response?.data as { detail?: string } | undefined)?.detail
        : undefined;
      showToast(detail || "Помилка активації", "error");
    },
  });

  const archiveMutation = useMutation({
    mutationFn: archiveStudent,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["students"] });
      showToast("Студента архівовано");
    },
    onError: () => showToast("Помилка архівації", "error"),
  });

  const bulkMutation = useMutation({
    mutationFn: bulkImportStudents,
    onSuccess: async (data) => {
      setBulkResult(JSON.stringify(data, null, 2));
      await queryClient.invalidateQueries({ queryKey: ["students"] });
      showToast("Імпорт виконано");
    },
    onError: () => showToast("Помилка bulk імпорту", "error"),
  });

  const toCanonicalMutation = useMutation({
    mutationFn: syncStudentToCanonical,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["sync", "jobs"] }),
        queryClient.invalidateQueries({ queryKey: ["repositories"] }),
      ]);
      showToast("Завантажено в master репозиторій");
    },
    onError: (error) => {
      const detail = axios.isAxiosError(error)
        ? (error.response?.data as { detail?: string } | undefined)?.detail
        : undefined;
      showToast(detail || "Помилка вивантаження в master", "error");
    },
  });

  const filteredStudents = useMemo(() => {
    const query = search.trim().toLowerCase();
    return (studentsQuery.data || []).filter((student) => student.full_name.toLowerCase().includes(query));
  }, [studentsQuery.data, search]);

  const openCreate = () => {
    setEditing(null);
    setForm({ full_name: "", email: "", notes: "", queue_position: "" });
    setDialogOpen(true);
  };

  const openEdit = (student: Student) => {
    setEditing(student);
    setForm({
      full_name: student.full_name || "",
      email: student.email || "",
      notes: student.notes || "",
      queue_position: student.queue_position?.toString() || "",
    });
    setDialogOpen(true);
  };

  const onSave = () => {
    if (!form.full_name.trim()) {
      showToast("Вкажіть повне ім'я", "error");
      return;
    }
    saveMutation.mutate();
  };

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "center" }}>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
          + Додати студента
        </Button>
        <Button variant="outlined" startIcon={<UploadFileIcon />} onClick={() => setBulkOpen(true)}>
          Bulk Import
        </Button>
        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => studentsQuery.refetch()}>
          Оновити
        </Button>
        <TextField
          size="small"
          label="Пошук"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ ml: { md: "auto" }, minWidth: 220 }}
        />
      </Stack>

      {studentsQuery.isLoading ? (
        <LoadingState />
      ) : studentsQuery.error ? (
        <Alert severity="error" action={<Button onClick={() => studentsQuery.refetch()}>Повторити</Button>}>
          Не вдалося завантажити студентів
        </Alert>
      ) : (
        <Paper sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>#</TableCell>
                <TableCell>Повне ім'я</TableCell>
                <TableCell>Статус</TableCell>
                <TableCell>Позиція черги</TableCell>
                <TableCell>Нотатки</TableCell>
                <TableCell>Дії</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredStudents.map((student) => (
                <TableRow key={student.id} hover>
                  <TableCell>{student.queue_position ?? "—"}</TableCell>
                  <TableCell>
                    <Button variant="text" onClick={() => openEdit(student)}>
                      {student.full_name}
                    </Button>
                  </TableCell>
                  <TableCell>{statusChip(student.status)}</TableCell>
                  <TableCell>{student.queue_position ?? "—"}</TableCell>
                  <TableCell>{student.notes?.slice(0, 60) || "—"}</TableCell>
                  <TableCell>
                    <Tooltip title="Редагувати">
                      <IconButton onClick={() => openEdit(student)}>
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Синхронізувати з master">
                      <IconButton onClick={() => activateMutation.mutate(student.id)}>
                        <PlayArrowIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Вигрузити в master">
                      <IconButton onClick={() => toCanonicalMutation.mutate(student.id)}>
                        <UploadFileIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Архівувати">
                      <IconButton onClick={() => archiveMutation.mutate(student.id)}>
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{editing ? "Редагувати студента" : "Додати студента"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Повне ім'я"
              value={form.full_name}
              onChange={(e) => setForm((p) => ({ ...p, full_name: e.target.value }))}
              required
            />
            <TextField
              label="Email"
              value={form.email}
              onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
            />
            <TextField
              label="Нотатки"
              multiline
              minRows={3}
              value={form.notes}
              onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))}
            />
            <TextField
              label="Позиція черги"
              type="number"
              value={form.queue_position}
              onChange={(e) => setForm((p) => ({ ...p, queue_position: e.target.value }))}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Скасувати</Button>
          <Button variant="contained" onClick={onSave} disabled={saveMutation.isPending}>
            Зберегти
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={bulkOpen} onClose={() => setBulkOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>Bulk Import</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="JSON масив"
              multiline
              minRows={8}
              value={bulkPayload}
              onChange={(e) => setBulkPayload(e.target.value)}
            />
            {bulkResult && <TextField label="Результат" multiline minRows={6} value={bulkResult} />}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBulkOpen(false)}>Закрити</Button>
          <Button
            variant="contained"
            onClick={() => {
              try {
                const parsed = JSON.parse(bulkPayload) as Array<{
                  full_name: string;
                  email?: string;
                  repo_url?: string;
                  pat?: string;
                  password?: string;
                }>;
                bulkMutation.mutate(parsed);
              } catch {
                showToast("Невалідний JSON", "error");
              }
            }}
          >
            Імпортувати
          </Button>
        </DialogActions>
      </Dialog>

      <ActionSnackbar toast={toast} onClose={() => setToast((t) => ({ ...t, open: false }))} />
    </Stack>
  );
}

function AccountsPage() {
  const queryClient = useQueryClient();
  const { toast, setToast, showToast } = useToast();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [form, setForm] = useState({ student_id: "", username: "", provider: "github", auth_type: "pat" });

  const accountsQuery = useQuery({ queryKey: ["accounts"], queryFn: fetchAccounts });
  const studentsQuery = useQuery({ queryKey: ["students"], queryFn: () => fetchStudents() });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editing) {
        return updateAccount({ id: editing.id, ...form });
      }
      return createAccount(form);
    },
    onSuccess: async () => {
      setDialogOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["accounts"] });
      showToast("Акаунт збережено");
    },
    onError: () => showToast("Помилка збереження акаунта", "error"),
  });

  const setCurrentMutation = useMutation({
    mutationFn: setCurrentAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      showToast("Позначено поточним");
    },
    onError: () => showToast("Помилка оновлення", "error"),
  });

  const markValidatedMutation = useMutation({
    mutationFn: markValidated,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      showToast("Позначено як перевірений");
    },
    onError: () => showToast("Помилка оновлення", "error"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      showToast("Акаунт деактивовано");
    },
    onError: () => showToast("Помилка видалення", "error"),
  });

  const studentMap = useMemo(() => {
    const map = new Map<string, Student>();
    (studentsQuery.data || []).forEach((student) => map.set(student.id, student));
    return map;
  }, [studentsQuery.data]);

  const openCreate = () => {
    setEditing(null);
    setForm({ student_id: studentsQuery.data?.[0]?.id || "", username: "", provider: "github", auth_type: "pat" });
    setDialogOpen(true);
  };

  const openEdit = (account: Account) => {
    setEditing(account);
    setForm({
      student_id: account.student_id,
      username: account.username,
      provider: account.provider,
      auth_type: account.auth_type,
    });
    setDialogOpen(true);
  };

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
          + Додати акаунт
        </Button>
        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => accountsQuery.refetch()}>
          Оновити
        </Button>
      </Stack>

      {accountsQuery.isLoading ? (
        <LoadingState />
      ) : accountsQuery.error ? (
        <Alert severity="error" action={<Button onClick={() => accountsQuery.refetch()}>Повторити</Button>}>
          Не вдалося завантажити акаунти
        </Alert>
      ) : (
        <Paper sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Логін</TableCell>
                <TableCell>Провайдер</TableCell>
                <TableCell>Тип авт.</TableCell>
                <TableCell>Статус</TableCell>
                <TableCell>Студент</TableCell>
                <TableCell>Остання перевірка</TableCell>
                <TableCell>Дії</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(accountsQuery.data || []).map((account) => (
                <TableRow key={account.id}>
                  <TableCell>{account.username}</TableCell>
                  <TableCell>{account.provider}</TableCell>
                  <TableCell>{statusChip(account.auth_type)}</TableCell>
                  <TableCell>{statusChip(account.status || "active")}</TableCell>
                  <TableCell>{studentMap.get(account.student_id)?.full_name || account.student_id}</TableCell>
                  <TableCell>{formatDate(account.last_validated_at)}</TableCell>
                  <TableCell>
                    <Button size="small" onClick={() => setCurrentMutation.mutate(account.id)}>
                      Поточний
                    </Button>
                    <Button size="small" onClick={() => markValidatedMutation.mutate(account.id)}>
                      Перевірено
                    </Button>
                    <IconButton onClick={() => openEdit(account)}>
                      <EditIcon />
                    </IconButton>
                    <IconButton onClick={() => deleteMutation.mutate(account.id)}>
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{editing ? "Редагувати акаунт" : "Додати акаунт"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <FormControl fullWidth>
              <InputLabel>Студент</InputLabel>
              <Select
                value={form.student_id}
                label="Студент"
                onChange={(e) => setForm((p) => ({ ...p, student_id: e.target.value }))}
              >
                {(studentsQuery.data || []).map((student) => (
                  <MenuItem key={student.id} value={student.id}>
                    {student.full_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="Логін (username)"
              value={form.username}
              onChange={(e) => setForm((p) => ({ ...p, username: e.target.value }))}
            />
            <FormControl fullWidth>
              <InputLabel>Провайдер</InputLabel>
              <Select
                value={form.provider}
                label="Провайдер"
                onChange={(e) => setForm((p) => ({ ...p, provider: e.target.value }))}
              >
                <MenuItem value="github">GitHub</MenuItem>
                <MenuItem value="gitlab">GitLab</MenuItem>
                <MenuItem value="bitbucket">Bitbucket</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Тип авторизації</InputLabel>
              <Select
                value={form.auth_type}
                label="Тип авторизації"
                onChange={(e) => setForm((p) => ({ ...p, auth_type: e.target.value }))}
              >
                <MenuItem value="pat">PAT</MenuItem>
                <MenuItem value="ssh">SSH</MenuItem>
                <MenuItem value="oauth">OAuth</MenuItem>
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Скасувати</Button>
          <Button variant="contained" onClick={() => saveMutation.mutate()}>
            Зберегти
          </Button>
        </DialogActions>
      </Dialog>

      <ActionSnackbar toast={toast} onClose={() => setToast((t) => ({ ...t, open: false }))} />
    </Stack>
  );
}

function CredentialsPage() {
  const queryClient = useQueryClient();
  const { toast, setToast, showToast } = useToast();
  const [addOpen, setAddOpen] = useState(false);
  const [rotateOpen, setRotateOpen] = useState(false);
  const [selected, setSelected] = useState<Credential | null>(null);
  const [showSecret, setShowSecret] = useState(false);
  const [showRotateSecret, setShowRotateSecret] = useState(false);
  const [form, setForm] = useState({ account_id: "", auth_type: "pat", secret: "" });
  const [rotateSecret, setRotateSecret] = useState("");

  const credentialsQuery = useQuery({ queryKey: ["credentials"], queryFn: fetchCredentials });
  const accountsQuery = useQuery({ queryKey: ["accounts"], queryFn: fetchAccounts });

  const createMutation = useMutation({
    mutationFn: createCredential,
    onSuccess: async () => {
      setAddOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["credentials"] });
      showToast("Облікові дані додано");
    },
    onError: () => showToast("Помилка збереження", "error"),
  });

  const rotateMutation = useMutation({
    mutationFn: ({ id, secret }: { id: string; secret: string }) => rotateCredential(id, secret),
    onSuccess: async () => {
      setRotateOpen(false);
      setRotateSecret("");
      await queryClient.invalidateQueries({ queryKey: ["credentials"] });
      showToast("Секрет ротовано");
    },
    onError: () => showToast("Помилка ротації", "error"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCredential,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["credentials"] });
      showToast("Секрет видалено");
    },
    onError: () => showToast("Помилка видалення", "error"),
  });

  const existsMutation = useMutation({
    mutationFn: checkCredentialExists,
    onSuccess: (result) => showToast(result.exists ? "Секрет знайдено в keyring" : "Секрет не знайдено", result.exists ? "success" : "error"),
    onError: () => showToast("Помилка перевірки", "error"),
  });

  const accountMap = useMemo(() => {
    const map = new Map<string, Account>();
    (accountsQuery.data || []).forEach((account) => map.set(account.id, account));
    return map;
  }, [accountsQuery.data]);

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => {
            setForm({ account_id: accountsQuery.data?.[0]?.id || "", auth_type: "pat", secret: "" });
            setAddOpen(true);
          }}
        >
          + Додати
        </Button>
        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => credentialsQuery.refetch()}>
          Оновити
        </Button>
      </Stack>

      {credentialsQuery.isLoading ? (
        <LoadingState />
      ) : credentialsQuery.error ? (
        <Alert severity="error" action={<Button onClick={() => credentialsQuery.refetch()}>Повторити</Button>}>
          Не вдалося завантажити облікові дані
        </Alert>
      ) : (
        <Paper sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Акаунт</TableCell>
                <TableCell>Тип авт.</TableCell>
                <TableCell>Секрет (замаскований)</TableCell>
                <TableCell>Остання перевірка</TableCell>
                <TableCell>Дії</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(credentialsQuery.data || []).map((credential) => {
                const masked =
                  credential.masked_secret ||
                  (credential.secret_ref ? `••••••••${credential.secret_ref.slice(-4)}` : "••••");
                return (
                  <TableRow key={credential.id}>
                    <TableCell>{accountMap.get(credential.account_id || "")?.username || credential.account_id || "—"}</TableCell>
                    <TableCell>{statusChip(credential.auth_type || credential.secret_kind || "pat")}</TableCell>
                    <TableCell sx={{ fontFamily: "monospace" }}>{masked}</TableCell>
                    <TableCell>{formatDate(credential.last_validated_at)}</TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        onClick={() => {
                          setSelected(credential);
                          setRotateOpen(true);
                        }}
                      >
                        Ротувати
                      </Button>
                      <Button size="small" onClick={() => existsMutation.mutate(credential.id)}>
                        Exists?
                      </Button>
                      <IconButton onClick={() => deleteMutation.mutate(credential.id)}>
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Paper>
      )}

      <Dialog open={addOpen} onClose={() => setAddOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Додати облікові дані</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <FormControl fullWidth>
              <InputLabel>Акаунт</InputLabel>
              <Select
                value={form.account_id}
                label="Акаунт"
                onChange={(e) => setForm((p) => ({ ...p, account_id: e.target.value }))}
              >
                {(accountsQuery.data || []).map((acc) => (
                  <MenuItem value={acc.id} key={acc.id}>
                    {acc.username}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Тип авт.</InputLabel>
              <Select
                value={form.auth_type}
                label="Тип авт."
                onChange={(e) => setForm((p) => ({ ...p, auth_type: e.target.value }))}
              >
                <MenuItem value="pat">PAT</MenuItem>
                <MenuItem value="ssh">SSH</MenuItem>
                <MenuItem value="oauth">OAuth</MenuItem>
              </Select>
            </FormControl>

            <TextField
              type={showSecret ? "text" : "password"}
              label="Токен / PAT"
              value={form.secret}
              onChange={(e) => setForm((p) => ({ ...p, secret: e.target.value }))}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowSecret((v) => !v)}>
                      {showSecret ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <Typography variant="caption" color="text.secondary">
              Секрет зберігається в OS keyring, не в базі даних
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddOpen(false)}>Скасувати</Button>
          <Button variant="contained" onClick={() => createMutation.mutate(form)}>
            Зберегти
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={rotateOpen} onClose={() => setRotateOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Ротація секрету</DialogTitle>
        <DialogContent>
          <TextField
            sx={{ mt: 1 }}
            type={showRotateSecret ? "text" : "password"}
            fullWidth
            label="Новий PAT/токен"
            value={rotateSecret}
            onChange={(e) => setRotateSecret(e.target.value)}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowRotateSecret((v) => !v)}>
                    {showRotateSecret ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRotateOpen(false)}>Скасувати</Button>
          <Button
            variant="contained"
            onClick={() => {
              if (selected) rotateMutation.mutate({ id: selected.id, secret: rotateSecret });
            }}
          >
            Підтвердити
          </Button>
        </DialogActions>
      </Dialog>

      <ActionSnackbar toast={toast} onClose={() => setToast((t) => ({ ...t, open: false }))} />
    </Stack>
  );
}

function RepositoriesPage() {
  const queryClient = useQueryClient();
  const { toast, setToast, showToast } = useToast();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Repository | null>(null);
  const [showCanonical, setShowCanonical] = useState(false);
  const [form, setForm] = useState({ student_id: "", url: "", branch: "main", local_path: "" });

  const reposQuery = useQuery({ queryKey: ["repositories"], queryFn: fetchRepositories });
  const studentsQuery = useQuery({ queryKey: ["students"], queryFn: () => fetchStudents() });
  const canonicalQuery = useQuery({ queryKey: ["repositories", "canonical"], queryFn: fetchCanonicalRepository });
  const canonicalSettingsQuery = useQuery({
    queryKey: ["settings", "canonical"],
    queryFn: fetchBackendSettings,
  });

  const canonicalSettings = useMemo(() => {
    const list = canonicalSettingsQuery.data || [];
    const getValue = (key: string) => list.find((item) => item.key === key)?.value || "";
    return {
      remoteUrl: getValue("canonical_remote_url"),
      localPath: getValue("canonical_repo_path"),
      branch: getValue("default_branch") || "main",
    };
  }, [canonicalSettingsQuery.data]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editing) {
        return updateRepository({ id: editing.id, url: form.url, branch: form.branch, local_path: form.local_path });
      }
      return createRepository(form);
    },
    onSuccess: async () => {
      setDialogOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["repositories"] });
      showToast("Репозиторій збережено");
    },
    onError: () => showToast("Помилка збереження репозиторію", "error"),
  });

  const validateMutation = useMutation({
    mutationFn: validateRepositoryRemote,
    onSuccess: (data) => showToast(data.remote_reachable ? "Remote доступний" : "Remote недоступний", data.remote_reachable ? "success" : "error"),
    onError: () => showToast("Помилка перевірки remote", "error"),
  });

  const statusMutation = useMutation({
    mutationFn: fetchRepositoryStatus,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["repositories"] });
      showToast("Статус оновлено");
    },
    onError: () => showToast("Помилка завантаження статусу", "error"),
  });

  const openCreate = () => {
    setEditing(null);
    setForm({ student_id: studentsQuery.data?.[0]?.id || "", url: "", branch: "main", local_path: "" });
    setDialogOpen(true);
  };

  const openEdit = (repo: Repository) => {
    setEditing(repo);
    setForm({
      student_id: repo.student_id || "",
      url: repo.url || repo.remote_url || "",
      branch: repo.branch || repo.default_branch || "main",
      local_path: repo.local_path || "",
    });
    setDialogOpen(true);
  };

  const hasCanonicalFallback = Boolean(canonicalSettings.localPath || canonicalSettings.remoteUrl);

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
          + Додати репозиторій
        </Button>
        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => reposQuery.refetch()}>
          Оновити
        </Button>
        <Button variant="outlined" onClick={() => setShowCanonical((v) => !v)}>
          Master репозиторій
        </Button>
      </Stack>

      {showCanonical && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography sx={{ fontWeight: 700 }}>Master репозиторій</Typography>
          </AccordionSummary>
          <AccordionDetails>
            {canonicalQuery.isLoading || canonicalSettingsQuery.isLoading ? (
              <CircularProgress size={18} />
            ) : canonicalQuery.data ? (
              <Stack spacing={1}>
                <Typography>Локальний шлях: {canonicalQuery.data.local_path || "—"}</Typography>
                <Typography>Remote URL: {canonicalQuery.data.remote_url || canonicalSettings.remoteUrl || "—"}</Typography>
                <Typography>Гілка: {canonicalQuery.data.branch || canonicalQuery.data.default_branch || canonicalSettings.branch || "—"}</Typography>
                <Typography>Остання синхронізація: {formatDate(canonicalQuery.data.updated_at)}</Typography>
              </Stack>
            ) : hasCanonicalFallback ? (
              <Stack spacing={1}>
                <Typography>Локальний шлях: {canonicalSettings.localPath || "—"}</Typography>
                <Typography>Remote URL: {canonicalSettings.remoteUrl || "—"}</Typography>
                <Typography>Гілка: {canonicalSettings.branch || "—"}</Typography>
                <Typography color="text.secondary">Показано із системних налаштувань (запис репозиторію ще не ініціалізований).</Typography>
              </Stack>
            ) : (
              <Typography color="text.secondary">Немає даних master репозиторію</Typography>
            )}
          </AccordionDetails>
        </Accordion>
      )}

      {reposQuery.isLoading ? (
        <LoadingState />
      ) : reposQuery.error ? (
        <Alert severity="error" action={<Button onClick={() => reposQuery.refetch()}>Повторити</Button>}>
          Не вдалося завантажити репозиторії
        </Alert>
      ) : (
        <Paper sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Назва репо</TableCell>
                <TableCell>Локальний шлях</TableCell>
                <TableCell>Remote URL</TableCell>
                <TableCell>Гілка</TableCell>
                <TableCell>Стан синхр.</TableCell>
                <TableCell>Останній коміт</TableCell>
                <TableCell>Дії</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(reposQuery.data || []).map((repo) => {
                const url = repo.url || repo.remote_url || "";
                const sha = repo.last_commit_sha || repo.last_commit_hash || "";
                return (
                  <TableRow key={repo.id}>
                    <TableCell>{repo.repo_name || url.split("/").pop() || "repo"}</TableCell>
                    <TableCell sx={{ fontFamily: "monospace" }}>{repo.local_path || "—"}</TableCell>
                    <TableCell>
                      <Tooltip title={url}>
                        <Typography noWrap sx={{ maxWidth: 220 }}>{url || "—"}</Typography>
                      </Tooltip>
                    </TableCell>
                    <TableCell>{statusChip(repo.branch || repo.default_branch || "main")}</TableCell>
                    <TableCell>{statusChip(repo.sync_status || "uninitialized")}</TableCell>
                    <TableCell>
                      {sha ? `${sha.slice(0, 7)} ${repo.last_commit_msg || ""}` : "—"}
                    </TableCell>
                    <TableCell>
                      <Button size="small" onClick={() => validateMutation.mutate(repo.id)}>
                        Перевірити
                      </Button>
                      <Button size="small" onClick={() => statusMutation.mutate(repo.id)}>
                        Статус
                      </Button>
                      <IconButton onClick={() => openEdit(repo)}>
                        <EditIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Paper>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{editing ? "Редагувати репозиторій" : "Додати репозиторій"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <FormControl fullWidth>
              <InputLabel>Студент</InputLabel>
              <Select
                value={form.student_id}
                label="Студент"
                onChange={(e) => setForm((p) => ({ ...p, student_id: e.target.value }))}
              >
                {(studentsQuery.data || []).map((student) => (
                  <MenuItem key={student.id} value={student.id}>
                    {student.full_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="Remote URL"
              value={form.url}
              onChange={(e) => setForm((p) => ({ ...p, url: e.target.value }))}
            />
            <TextField
              label="Гілка"
              value={form.branch}
              onChange={(e) => setForm((p) => ({ ...p, branch: e.target.value }))}
            />
            <TextField
              label="Локальний шлях"
              value={form.local_path}
              onChange={(e) => setForm((p) => ({ ...p, local_path: e.target.value }))}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Скасувати</Button>
          <Button variant="contained" onClick={() => saveMutation.mutate()}>
            Зберегти
          </Button>
        </DialogActions>
      </Dialog>

      <ActionSnackbar toast={toast} onClose={() => setToast((t) => ({ ...t, open: false }))} />
    </Stack>
  );
}

function PromptsPage() {
  const queryClient = useQueryClient();
  const { toast, setToast, showToast } = useToast();
  const [selectedId, setSelectedId] = useState<string>("");
  const [form, setForm] = useState({ title: "", file_path: "", student_id: "", content: "" });

  const promptsQuery = useQuery({ queryKey: ["prompts"], queryFn: fetchPrompts });
  const studentsQuery = useQuery({ queryKey: ["students"], queryFn: () => fetchStudents() });
  const selectedPromptQuery = useQuery({
    queryKey: ["prompts", selectedId],
    queryFn: () => fetchPromptById(selectedId),
    enabled: Boolean(selectedId),
  });

  useEffect(() => {
    if (selectedPromptQuery.data) {
      setForm({
        title: selectedPromptQuery.data.title || "",
        file_path: selectedPromptQuery.data.file_path || "",
        student_id: selectedPromptQuery.data.student_id || "",
        content: selectedPromptQuery.data.content || "",
      });
    }
  }, [selectedPromptQuery.data]);

  const saveMutation = useMutation({
    mutationFn: createPrompt,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["prompts"] });
      showToast("Промт збережено");
    },
    onError: () => showToast("Помилка збереження промту", "error"),
  });

  const retryMutation = useMutation({
    mutationFn: retryPrompt,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["prompts"] });
      showToast("Повторну відправку запущено");
    },
    onError: () => showToast("Помилка retry", "error"),
  });

  return (
    <Stack spacing={2}>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "3fr 2fr" }, gap: 2 }}>
        <Paper sx={{ p: 2, overflowX: "auto" }}>
          <Typography variant="h6" sx={{ mb: 1.5, fontWeight: 700 }}>
            Список промтів
          </Typography>
          {promptsQuery.isLoading ? (
            <LoadingState />
          ) : promptsQuery.error ? (
            <Alert severity="error" action={<Button onClick={() => promptsQuery.refetch()}>Повторити</Button>}>
              Не вдалося завантажити промти
            </Alert>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>#</TableCell>
                  <TableCell>Назва</TableCell>
                  <TableCell>Файл</TableCell>
                  <TableCell>Статус</TableCell>
                  <TableCell>Відправлено</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(promptsQuery.data || []).map((prompt, idx) => (
                  <TableRow key={prompt.id} hover selected={selectedId === prompt.id} onClick={() => setSelectedId(prompt.id)}>
                    <TableCell>{idx + 1}</TableCell>
                    <TableCell>{prompt.title}</TableCell>
                    <TableCell>{prompt.file_path}</TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={1} alignItems="center">
                        {statusChip(prompt.status)}
                        {prompt.status === "failed" && (
                          <Button
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              retryMutation.mutate(prompt.id);
                            }}
                          >
                            Повторити
                          </Button>
                        )}
                      </Stack>
                    </TableCell>
                    <TableCell>{formatDate(prompt.pushed_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Paper>

        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1.5, fontWeight: 700 }}>
            Редактор промту
          </Typography>
          <Stack spacing={1.5}>
            <TextField
              label="Назва промту"
              value={form.title}
              onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
            />
            <TextField
              label="Шлях до файлу"
              value={form.file_path}
              onChange={(e) => setForm((p) => ({ ...p, file_path: e.target.value }))}
            />
            <FormControl fullWidth>
              <InputLabel>Студент</InputLabel>
              <Select
                value={form.student_id}
                label="Студент"
                onChange={(e) => setForm((p) => ({ ...p, student_id: e.target.value }))}
              >
                <MenuItem value="">Усі</MenuItem>
                {(studentsQuery.data || []).map((student) => (
                  <MenuItem value={student.id} key={student.id}>
                    {student.full_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="Вміст промту"
              multiline
              minRows={12}
              value={form.content}
              onChange={(e) => setForm((p) => ({ ...p, content: e.target.value }))}
            />
            <Stack direction="row" spacing={1}>
              <Button
                variant="outlined"
                onClick={() => saveMutation.mutate({ ...form, status: "draft", student_id: form.student_id || undefined })}
              >
                Зберегти чернетку
              </Button>
              <Button
                variant="contained"
                onClick={() => saveMutation.mutate({ ...form, status: "written", student_id: form.student_id || undefined })}
              >
                Відправити в репо
              </Button>
            </Stack>
          </Stack>
        </Paper>
      </Box>

      <ActionSnackbar toast={toast} onClose={() => setToast((t) => ({ ...t, open: false }))} />
    </Stack>
  );
}

function AuditPage() {
  const [entityType, setEntityType] = useState("");
  const [action, setAction] = useState("");

  const auditQuery = useQuery({
    queryKey: ["audit", entityType, action],
    queryFn: () => fetchAudit(entityType || undefined, action || undefined),
  });

  const exportCsv = (items: AuditItem[]) => {
    const escapeValue = (value: string) => `"${value.replace(/"/g, '""')}"`;
    const rows = [
      ["timestamp", "actor", "action", "entity_type", "entity_id", "details"],
      ...items.map((item) => [
        item.timestamp || "",
        item.actor || "",
        item.action || "",
        item.entity_type || "",
        item.entity_id || "",
        item.details || "",
      ]),
    ];

    const csv = rows.map((row) => row.map((cell) => escapeValue(String(cell))).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "audit-log.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Тип сутності</InputLabel>
          <Select value={entityType} label="Тип сутності" onChange={(e) => setEntityType(e.target.value)}>
            <MenuItem value="">Усі</MenuItem>
            <MenuItem value="student">student</MenuItem>
            <MenuItem value="account">account</MenuItem>
            <MenuItem value="credential">credential</MenuItem>
            <MenuItem value="repository">repository</MenuItem>
            <MenuItem value="sync">sync</MenuItem>
            <MenuItem value="handoff">handoff</MenuItem>
            <MenuItem value="prompt">prompt</MenuItem>
          </Select>
        </FormControl>
        <TextField size="small" label="Дія" value={action} onChange={(e) => setAction(e.target.value)} />
        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => auditQuery.refetch()}>
          Оновити
        </Button>
        <Button
          variant="contained"
          startIcon={<FileDownloadIcon />}
          onClick={() => exportCsv(auditQuery.data || [])}
          disabled={!auditQuery.data?.length}
        >
          Експорт CSV
        </Button>
      </Stack>

      {auditQuery.isLoading ? (
        <LoadingState />
      ) : auditQuery.error ? (
        <Alert severity="error" action={<Button onClick={() => auditQuery.refetch()}>Повторити</Button>}>
          Не вдалося завантажити журнал
        </Alert>
      ) : (
        <Paper sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Timestamp</TableCell>
                <TableCell>Actor</TableCell>
                <TableCell>Дія</TableCell>
                <TableCell>Тип</TableCell>
                <TableCell>ID сутності</TableCell>
                <TableCell>Деталі</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(auditQuery.data || []).map((item, idx) => (
                <TableRow key={item.id || `${item.timestamp}-${idx}`}>
                  <TableCell>{formatDate(item.timestamp)}</TableCell>
                  <TableCell>{item.actor || "—"}</TableCell>
                  <TableCell>{item.action || "—"}</TableCell>
                  <TableCell>{statusChip(item.entity_type)}</TableCell>
                  <TableCell>{item.entity_id || "—"}</TableCell>
                  <TableCell>
                    <Tooltip title={item.details || ""}>
                      <Typography noWrap sx={{ maxWidth: 260 }}>{item.details || "—"}</Typography>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Stack>
  );
}

function SettingsPage() {
  const queryClient = useQueryClient();
  const { toast, setToast, showToast } = useToast();
  const runtime = getRuntimeConfig();
  const [apiUrl, setApiUrl] = useState(runtime.apiUrl || "");
  const [apiToken, setApiToken] = useState(runtime.apiToken || "");
  const [showToken, setShowToken] = useState(false);
  const [newSettingKey, setNewSettingKey] = useState("");
  const [newSettingValue, setNewSettingValue] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});

  const backendSettingsQuery = useQuery({ queryKey: ["settings"], queryFn: fetchBackendSettings });

  const SETTINGS_LABELS: Record<string, string> = {
    auto_sync_interval_minutes: "Інтервал автосинхронізації (хв)",
    canonical_remote_url: "Remote URL master репозиторію",
    canonical_repo_path: "Локальний шлях master репозиторію",
    default_branch: "Гілка за замовчуванням",
    enable_auto_sync: "Увімкнути автосинхронізацію",
    max_sync_retries: "Максимум повторних sync-спроб",
    sync_timeout_seconds: "Таймаут sync (сек)",
    template_dir: "Каталог шаблонів",
  };

  useEffect(() => {
    const nextValues: Record<string, string> = {};
    (backendSettingsQuery.data || []).forEach((setting: SettingItem) => {
      nextValues[setting.key] = setting.value;
    });
    setValues(nextValues);
  }, [backendSettingsQuery.data]);

  const checkMutation = useMutation({
    mutationFn: healthCheck,
    onSuccess: () => showToast("З'єднання успішне"),
    onError: () => showToast("З'єднання не встановлено", "error"),
  });

  const saveSettingMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) => putBackendSetting(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      showToast("Параметр збережено");
    },
    onError: () => showToast("Помилка збереження параметра", "error"),
  });

  const deleteSettingMutation = useMutation({
    mutationFn: deleteBackendSetting,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      showToast("Параметр видалено");
    },
    onError: () => showToast("Помилка видалення параметра", "error"),
  });

  return (
    <Stack spacing={2}>
      <Paper sx={{ p: 2.5 }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
          API з'єднання
        </Typography>
        <Stack spacing={1.5}>
          <TextField label="API URL" value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} />
          <TextField
            label="API Token"
            type={showToken ? "text" : "password"}
            value={apiToken}
            onChange={(e) => setApiToken(e.target.value)}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowToken((v) => !v)}>
                    {showToken ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
          <Stack direction="row" spacing={1}>
            <Button
              variant="contained"
              onClick={() => {
                saveRuntimeConfig(apiUrl, apiToken);
                showToast("Конфігурацію збережено");
              }}
            >
              Зберегти
            </Button>
            <Button variant="outlined" onClick={() => checkMutation.mutate()}>
              Перевірити з'єднання
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2.5 }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
          Налаштування бекенду
        </Typography>

        {backendSettingsQuery.isLoading ? (
          <LoadingState />
        ) : backendSettingsQuery.error ? (
          <Alert severity="error" action={<Button onClick={() => backendSettingsQuery.refetch()}>Повторити</Button>}>
            Не вдалося завантажити налаштування
          </Alert>
        ) : (
          <Stack spacing={1}>
            {(backendSettingsQuery.data || []).map((setting) => (
              <Stack key={setting.key} direction={{ xs: "column", md: "row" }} spacing={1} alignItems={{ md: "center" }}>
                <Box sx={{ width: { md: 280 } }}>
                  <Typography sx={{ fontWeight: 600 }}>{SETTINGS_LABELS[setting.key] || setting.key}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {setting.key}
                  </Typography>
                </Box>
                <TextField
                  size="small"
                  fullWidth
                  value={values[setting.key] ?? ""}
                  onChange={(e) => setValues((prev) => ({ ...prev, [setting.key]: e.target.value }))}
                />
                <IconButton onClick={() => saveSettingMutation.mutate({ key: setting.key, value: values[setting.key] ?? "" })}>
                  <SaveIcon />
                </IconButton>
                <IconButton onClick={() => deleteSettingMutation.mutate(setting.key)}>
                  <DeleteIcon />
                </IconButton>
              </Stack>
            ))}

            <Divider sx={{ my: 1 }} />
            <Stack direction={{ xs: "column", md: "row" }} spacing={1}>
              <TextField
                size="small"
                label="Новий ключ"
                value={newSettingKey}
                onChange={(e) => setNewSettingKey(e.target.value)}
              />
              <TextField
                size="small"
                fullWidth
                label="Значення"
                value={newSettingValue}
                onChange={(e) => setNewSettingValue(e.target.value)}
              />
              <Button
                variant="outlined"
                onClick={() => {
                  if (!newSettingKey.trim()) {
                    showToast("Вкажіть ключ", "error");
                    return;
                  }
                  saveSettingMutation.mutate({ key: newSettingKey.trim(), value: newSettingValue });
                  setNewSettingKey("");
                  setNewSettingValue("");
                }}
              >
                + Додати параметр
              </Button>
            </Stack>
          </Stack>
        )}
      </Paper>

      <Paper sx={{ p: 2.5 }}>
        <Typography variant="h6" sx={{ mb: 1.5, fontWeight: 700 }}>
          Про застосунок
        </Typography>
        <Typography>Version: 1.0.0</Typography>
        <Typography>License: Elastic License 2.0</Typography>
        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
          <Button
            variant="text"
            component="a"
            target="_blank"
            rel="noreferrer"
            href="https://github.com/maxfraieho/Students-flow-API"
            endIcon={<LaunchIcon />}
          >
            GitHub
          </Button>
          <Button
            variant="text"
            component="a"
            target="_blank"
            rel="noreferrer"
            href="https://github.com/maxfraieho/Students-flow-API/releases"
            endIcon={<LaunchIcon />}
          >
            Завантажити десктоп-версію
          </Button>
        </Stack>
      </Paper>

      <ActionSnackbar toast={toast} onClose={() => setToast((t) => ({ ...t, open: false }))} />
    </Stack>
  );
}

function AppShell() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [live, setLive] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const drawerContent = (
    <Box sx={{ width: drawerWidth }}>
      <Stack
        direction="row"
        spacing={1.25}
        alignItems="center"
        sx={{ px: 2, py: 1.5, minHeight: 72 }}
      >
        <Avatar
          variant="rounded"
          sx={{ width: 34, height: 34, bgcolor: "secondary.main", color: "secondary.contrastText" }}
        >
          <PeopleIcon fontSize="small" />
        </Avatar>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
            StudentFlow
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1 }}>
            Навчання з Lovable
          </Typography>
        </Box>
      </Stack>
      <Divider />
      <List>
        {NAV_ITEMS.map((item) => (
          <ListItem key={item.path} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => {
                navigate(item.path);
                if (isMobile) setDrawerOpen(false);
              }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <Divider />
      <List>
        <ListItem disablePadding>
          <ListItemButton
            selected={location.pathname === "/settings"}
            onClick={() => {
              navigate("/settings");
              if (isMobile) setDrawerOpen(false);
            }}
          >
            <ListItemIcon>
              <SettingsIcon />
            </ListItemIcon>
            <ListItemText primary="Налаштування" />
          </ListItemButton>
        </ListItem>
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <AppBar
        position="fixed"
        sx={{
          zIndex: (t) => t.zIndex.drawer + 1,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          {isMobile && (
            <IconButton color="inherit" edge="start" sx={{ mr: 1 }} onClick={() => setDrawerOpen(true)}>
              <MenuIcon />
            </IconButton>
          )}
          <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.1, flexGrow: 1 }}>
            StudentFlow
          </Typography>
          <LiveChip live={live} />
          <IconButton color="inherit" sx={{ ml: 1 }} onClick={() => navigate("/settings")}>
            <SettingsIcon />
          </IconButton>
        </Toolbar>
        <LinearProgress sx={{ visibility: live ? "visible" : "hidden", opacity: 0.35 }} color="secondary" />
      </AppBar>

      {isMobile ? (
        <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} variant="temporary" ModalProps={{ keepMounted: true }}>
          {drawerContent}
        </Drawer>
      ) : (
        <Drawer
          variant="permanent"
          open
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            "& .MuiDrawer-paper": { width: drawerWidth, boxSizing: "border-box" },
          }}
        >
          {drawerContent}
        </Drawer>
      )}

      <Box component="main" sx={{ flexGrow: 1, p: 2.5, width: { md: `calc(100% - ${drawerWidth}px)` } }}>
        <Toolbar />
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage setLive={setLive} />} />
          <Route path="/students" element={<StudentsPage />} />
          <Route path="/accounts" element={<AccountsPage />} />
          <Route path="/credentials" element={<CredentialsPage />} />
          <Route path="/repositories" element={<RepositoriesPage />} />
          <Route path="/prompts" element={<PromptsPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Box>
    </Box>
  );
}

export default function App() {
  return <AppShell />;
}
