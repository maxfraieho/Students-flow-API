# Промт для Codex — Запуш фронтенд шаблон у репо першого студента

## Мета
Клонувати репозиторій першого активного студента, повністю замінити файли
чистим React + Vite + TypeScript + MUI шаблоном, та запушити назад.
Це підготує репо для імпорту в Lovable.

---

## Крок 1 — Знайди репозиторій першого студента

```bash
# Отримай список студентів та знайди першого активного
curl -s http://localhost:8050/api/students | python3 -c "
import sys, json
d = json.load(sys.stdin)
active = [s for s in d if s['status'] != 'archived']
active.sort(key=lambda s: (s.get('queue_position') or 9999, s.get('id') or 9999))
if not active:
    print('ERROR: no active students found')
    exit(1)
s = active[0]
print(f'Student: {s[\"full_name\"]}')
print(f'RepoID:  {s.get(\"repository_id\")}')
"
```

```bash
# Отримай URL репозиторію (підстав REPO_ID з попереднього кроку)
REPO_ID=<repo_id>
curl -s "http://localhost:8050/api/repositories/$REPO_ID" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d['url'])
"
```

---

## Крок 2 — Клонуй репо студента

```bash
REPO_URL=<url з попереднього кроку>
WORK_DIR="/tmp/studentflow-frontend-init"
rm -rf "$WORK_DIR"

# PAT зберігається в keyring — дістань його
STUDENT_NAME=<full_name студента>
PAT=$(python3 -c "
import keyring
token = keyring.get_password('studentflow', '$STUDENT_NAME')
print(token or '')
")

# Вбудуй PAT у URL для пушу
AUTH_URL=$(echo "$REPO_URL" | sed "s|https://|https://$PAT@|")

git clone "$AUTH_URL" "$WORK_DIR"
cd "$WORK_DIR"
```

---

## Крок 3 — Очисти репо (залиш тільки .git)

```bash
cd "$WORK_DIR"
git rm -rf . --quiet 2>/dev/null || true
find . -maxdepth 1 -not -name '.git' -not -name '.' -exec rm -rf {} + 2>/dev/null || true
```

---

## Крок 4 — Створи React + Vite + TypeScript шаблон

```bash
# Ініціалізуй Vite проект у temp директорії
cd /tmp
rm -rf vite-temp
npm create vite@latest vite-temp -- --template react-ts --yes 2>/dev/null || \
  npx create-vite@latest vite-temp --template react-ts

# Скопіюй у робочу директорію
cp -r /tmp/vite-temp/. "$WORK_DIR/"
cd "$WORK_DIR"

# Встанови залежності щоб package-lock.json актуальний
npm install
npm install @mui/material @emotion/react @emotion/styled @mui/icons-material axios
```

---

## Крок 5 — Додай файли конфігурації

```bash
cd "$WORK_DIR"

# .env.example (БЕЗ реальних секретів)
cat > .env.example << 'ENV'
VITE_API_URL=https://studentflow-api-gateway.maxfraieho.workers.dev
VITE_API_TOKEN=your_operator_token_here
ENV

# .gitignore
cat > .gitignore << 'IGNORE'
node_modules/
dist/
dist-ssr/
*.local
.env
.env.local
.env.production
IGNORE

# README
cat > README.md << 'README'
# StudentFlow Frontend

React + TypeScript + Material UI frontend for the StudentFlow sync system.

## Setup

1. Copy `.env.example` to `.env.local` and fill in your values:
   ```
   VITE_API_URL=https://studentflow-api-gateway.maxfraieho.workers.dev
   VITE_API_TOKEN=your_operator_token_here
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start development server:
   ```bash
   npm run dev
   ```

## License
Elastic License 2.0 — see [LICENSE](../LICENSE)
README
```

---

## Крок 6 — Commit та force push

```bash
cd "$WORK_DIR"
git add -A
git commit -m "init: React + Vite + TypeScript + MUI starter for Lovable import"

# Спробуй push (з PAT вже вбудований в AUTH_URL)
git push "$AUTH_URL" HEAD:main --force 2>/dev/null || \
git push "$AUTH_URL" HEAD:master --force

echo ""
echo "✅ Готово! Репозиторій: $REPO_URL"
echo "Наступний крок: https://lovable.dev → New Project → Import from GitHub → $REPO_URL"
```

---

## Примітки

- Якщо `npm create vite` недоступний — встанови Node.js: `nix-env -iA nixpkgs.nodejs`
- PAT береться з OS keyring через `python3 -c "import keyring; ..."`
- Секрети НЕ потрапляють у git
