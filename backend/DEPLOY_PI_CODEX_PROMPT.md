You are a deployment agent running on a Raspberry Pi.
Your job: deploy the StudentFlow FastAPI backend end-to-end.
Rules:
- Execute every shell command yourself using your shell tool.
- After each command check the exit code and output; if it failed, diagnose and fix before continuing.
- Never ask the user to run anything manually.
- Never skip a step.

---

## VARIABLES

Set these in your environment before running any commands:

```
REPO_URL="https://github.com/maxfraieho/Students-flow-API.git"
INSTALL_DIR="$HOME/studentflow-api"
BACKEND_DIR="$INSTALL_DIR/backend"
VENV="$INSTALL_DIR/.venv"
SERVICE="studentflow-api"
PORT=8000
LINUX_USER="$(whoami)"
HOME_DIR="$HOME"
```

---

## STEP 1 — System packages

Run:
```bash
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git curl \
  libdbus-1-dev libsecret-1-dev
```
Verify: `python3 --version` prints 3.9+. If not, abort and report.

---

## STEP 2 — Clone or update repository

Run:
```bash
if [ -d "$HOME/studentflow-api/.git" ]; then
  git -C "$HOME/studentflow-api" pull --ff-only
else
  git clone https://github.com/maxfraieho/Students-flow-API.git "$HOME/studentflow-api"
fi
```
Verify: directory `$HOME/studentflow-api/backend/run.py` exists.

---

## STEP 3 — Python venv and dependencies

Run:
```bash
python3 -m venv "$HOME/studentflow-api/.venv"
"$HOME/studentflow-api/.venv/bin/pip" install --upgrade pip -q
"$HOME/studentflow-api/.venv/bin/pip" install \
  -r "$HOME/studentflow-api/backend/requirements.txt" -q
"$HOME/studentflow-api/.venv/bin/pip" install keyrings.cryptfile -q
```
Verify:
```bash
"$HOME/studentflow-api/.venv/bin/python" \
  -c "import fastapi, uvicorn, sqlalchemy; print('imports OK')"
```
Must print `imports OK`.

---

## STEP 4 — Systemd service

Detect current user and home:
```bash
LINUX_USER="$(whoami)"
HOME_DIR="$HOME"
```

Write the service file:
```bash
sudo tee /etc/systemd/system/studentflow-api.service > /dev/null << EOF
[Unit]
Description=StudentFlow FastAPI Backend
After=network.target

[Service]
User=$LINUX_USER
WorkingDirectory=$HOME_DIR/studentflow-api/backend
Environment=PYTHON_KEYRING_BACKEND=keyrings.cryptfile.cryptfile.CryptFileKeyring
ExecStart=$HOME_DIR/studentflow-api/.venv/bin/python run.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable studentflow-api
sudo systemctl restart studentflow-api
sleep 6
sudo systemctl is-active studentflow-api
```
Must print `active`. If not, run:
```bash
sudo journalctl -u studentflow-api -n 50 --no-pager
```
Read the error, fix it, and restart.

Health check:
```bash
curl -s http://localhost:8000/api/health
```
Must return JSON. If connection refused, wait 3 more seconds and retry.

---

## STEP 5 — Bulk-import 20 students

Write the payload to a temp file to avoid quoting issues:
```bash
cat > /tmp/students.json << 'ENDJSON'
{
  "students": [
    {"full_name":"Emily Johnson",     "github_username":"student01","repo_url":"https://github.com/maxfraieho/comfort-hug-platform.git",          "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Michael Smith",     "github_username":"student02","repo_url":"https://github.com/maxfraieho/centered-greeting.git",              "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Olivia Brown",      "github_username":"student03","repo_url":"https://github.com/maxfraieho/welcome-page-creator.git",           "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"James Davis",       "github_username":"student04","repo_url":"https://github.com/maxfraieho/equus-welcome-stage.git",            "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Sophia Wilson",     "github_username":"student05","repo_url":"https://github.com/maxfraieho/sweet-greeting-page.git",            "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"William Miller",    "github_username":"student06","repo_url":"https://github.com/maxfraieho/centered-welcome-page.git",          "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Ava Moore",         "github_username":"student07","repo_url":"https://github.com/maxfraieho/welcome-duck-centered.git",          "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Benjamin Taylor",   "github_username":"student08","repo_url":"https://github.com/maxfraieho/center-stage-greeting.git",          "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Charlotte Anderson","github_username":"student09","repo_url":"https://github.com/maxfraieho/centered-greeting-8ee5fb1f.git",     "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Daniel Thomas",     "github_username":"student10","repo_url":"https://github.com/maxfraieho/centered-welcome-pig.git",           "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Mia Jackson",       "github_username":"student11","repo_url":"https://github.com/maxfraieho/welcome-page.git",                   "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Alexander White",   "github_username":"student12","repo_url":"https://github.com/maxfraieho/centered-welcome-page-0839a8f0.git", "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Abigail Harris",    "github_username":"student13","repo_url":"https://github.com/maxfraieho/centered-greeting-54c71aca.git",     "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Joseph Martin",     "github_username":"student14","repo_url":"https://github.com/maxfraieho/centered-greeting-dc6ab9fe.git",     "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Emma Thompson",     "github_username":"student15","repo_url":"https://github.com/maxfraieho/welcome-page-5e8eea5d.git",          "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Matthew Garcia",    "github_username":"student16","repo_url":"https://github.com/maxfraieho/welcome-center.git",                 "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Harper Martinez",   "github_username":"student17","repo_url":"https://github.com/maxfraieho/welcome-center-80896e62.git",        "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"David Robinson",    "github_username":"student18","repo_url":"https://github.com/maxfraieho/welcome-page-951c20cc.git",          "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Grace Clark",       "github_username":"student19","repo_url":"https://github.com/maxfraieho/welcome-page-central.git",           "pat":"YOUR_SHARED_PAT_HERE"},
    {"full_name":"Christopher Lewis", "github_username":"student20","repo_url":"https://github.com/maxfraieho/welcome-page-pro.git",               "pat":"YOUR_SHARED_PAT_HERE"}
  ]
}
ENDJSON

curl -s -X POST http://localhost:8000/api/students/bulk-import \
  -H "Content-Type: application/json" \
  -d @/tmp/students.json
```

Parse the response. `created` must equal 20, `failed` must equal 0.
If any student failed, read the `error` field and fix before continuing.

---

## STEP 6 — Configure canonical repository

```bash
CANONICAL_PATH="/var/studentflow/repos/canonical"
CANONICAL_REMOTE="https://github.com/maxfraieho/Students-flow-API.git"

sudo mkdir -p "$CANONICAL_PATH"
sudo chown "$(whoami):$(whoami)" "$CANONICAL_PATH"

curl -s -X PUT http://localhost:8000/api/settings/canonical_repo_path \
  -H "Content-Type: application/json" \
  -d "{\"value\": \"$CANONICAL_PATH\"}"

curl -s -X PUT http://localhost:8000/api/settings/canonical_remote_url \
  -H "Content-Type: application/json" \
  -d "{\"value\": \"$CANONICAL_REMOTE\"}"

git clone "$CANONICAL_REMOTE" "$CANONICAL_PATH"
```

Verify: `ls "$CANONICAL_PATH"` shows repo files.

---

## STEP 7 — Smoke tests

Run each check and print PASS or FAIL:

```bash
BASE="http://localhost:8000"

pass_fail() {
  local label="$1" result="$2" expect="$3"
  if echo "$result" | grep -q "$expect"; then
    echo "PASS: $label"
  else
    echo "FAIL: $label"
    echo "  got: $result"
  fi
}

pass_fail "health"          "$(curl -s $BASE/api/health)"           "ok"
pass_fail "list students"   "$(curl -s $BASE/api/students)"         "Emily Johnson"
pass_fail "last student"    "$(curl -s $BASE/api/students)"         "Christopher Lewis"
pass_fail "active student"  "$(curl -s $BASE/api/students/active)"  "status"
pass_fail "swagger ui"      "$(curl -s $BASE/api/docs)"             "swagger"
```

All five must print PASS. If any FAIL, diagnose and fix.

---

## STEP 8 — Final report

Print exactly this block (fill in actual values):

```
============================================
  StudentFlow backend — deployment complete
============================================
  Service : studentflow-api (active)
  API     : http://localhost:8000
  Docs    : http://localhost:8000/api/docs
  DB      : ~/.studentflow/studentflow.db
  Students: 20 active in database
  Keyring : keyrings.cryptfile (headless)
============================================
```
