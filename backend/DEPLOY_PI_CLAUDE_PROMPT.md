You are deploying the **StudentFlow FastAPI backend** on this Raspberry Pi.
Work autonomously: run every shell command yourself, verify the result, and fix
any errors before moving on. Do NOT ask the user to run commands manually.

---

## 0. Variables (adjust only if the paths differ on this system)

```
REPO_URL="https://github.com/maxfraieho/Students-flow-API.git"
INSTALL_DIR="$HOME/studentflow-api"
BACKEND_DIR="$INSTALL_DIR/backend"
SERVICE_NAME="studentflow-api"
API_PORT=8000
VENV="$INSTALL_DIR/.venv"
```

---

## 1. System packages

```bash
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git curl \
  libdbus-1-dev libsecret-1-dev
```

Verify: `python3 --version` must print 3.9 or higher.

---

## 2. Clone / update the repository

```bash
if [ -d "$INSTALL_DIR/.git" ]; then
  git -C "$INSTALL_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi
```

---

## 3. Python virtual environment + dependencies

```bash
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip -q
"$VENV/bin/pip" install -r "$BACKEND_DIR/requirements.txt" -q
# headless keyring backend (no D-Bus / GNOME Keyring needed)
"$VENV/bin/pip" install keyrings.cryptfile -q
```

Verify: `"$VENV/bin/python" -c "import fastapi, uvicorn, sqlalchemy; print('OK')"`.

---

## 4. Systemd service

Create the file `/etc/systemd/system/$SERVICE_NAME.service`:

```ini
[Unit]
Description=StudentFlow FastAPI Backend
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/studentflow-api/backend
Environment=PYTHON_KEYRING_BACKEND=keyrings.cryptfile.cryptfile.CryptFileKeyring
ExecStart=/home/pi/studentflow-api/.venv/bin/python run.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

> If the current Linux user is NOT `pi`, replace `User=pi` and
> `/home/pi/...` paths with the actual username and home directory.

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"
```

Wait 5 seconds, then verify:

```bash
sleep 5
sudo systemctl is-active "$SERVICE_NAME"   # must print "active"
curl -s http://localhost:"$API_PORT"/api/health  # must return JSON
```

If the service failed, run `sudo journalctl -u "$SERVICE_NAME" -n 40 --no-pager`
and fix the root cause before continuing.

---

## 5. Bulk-import 20 students

Once the API responds, send the full student list:

```bash
curl -s -X POST http://localhost:"$API_PORT"/api/students/bulk-import \
  -H "Content-Type: application/json" \
  -d '{
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
}'
```

Expected output: `"created":20,"skipped":0,"failed":0`.
If any failed, inspect the `error` field per item and fix before proceeding.

---

## 6. Configure canonical repository

The canonical repo is the **instructor's** Git repository that will be broadcast
to all students. Set its local path and remote URL:

```bash
# Path where you want the canonical repo cloned on this Pi
CANONICAL_PATH="/var/studentflow/repos/canonical"
CANONICAL_REMOTE="https://github.com/maxfraieho/Students-flow-API.git"

sudo mkdir -p "$CANONICAL_PATH"
sudo chown pi:pi "$CANONICAL_PATH"   # adjust user if not pi

curl -s -X PUT http://localhost:"$API_PORT"/api/settings/canonical_repo_path \
  -H "Content-Type: application/json" \
  -d "{\"value\": \"$CANONICAL_PATH\"}"

curl -s -X PUT http://localhost:"$API_PORT"/api/settings/canonical_remote_url \
  -H "Content-Type: application/json" \
  -d "{\"value\": \"$CANONICAL_REMOTE\"}"
```

Then clone the canonical repo locally:

```bash
git clone "$CANONICAL_REMOTE" "$CANONICAL_PATH"
```

---

## 7. Smoke test — verify every critical endpoint

Run all checks and print PASS/FAIL for each:

```bash
BASE="http://localhost:$API_PORT"

check() {
  local label="$1" url="$2" expect="$3"
  result=$(curl -s "$url")
  if echo "$result" | grep -q "$expect"; then
    echo "PASS: $label"
  else
    echo "FAIL: $label → $result"
  fi
}

check "health"           "$BASE/api/health"                        "ok"
check "students list"    "$BASE/api/students"                      "Emily Johnson"
check "active student"   "$BASE/api/students/active"               "status"
check "students count"   "$BASE/api/students"                      "Christopher Lewis"
check "broadcast opens"  "$BASE/api/sync/broadcast"                "broadcast_start"
```

All must print PASS. Fix any FAILs before reporting done.

---

## 8. Report

When all checks pass, print a summary:

```
StudentFlow backend deployed successfully.
  Service:  systemctl status studentflow-api
  API:      http://localhost:8000
  Docs:     http://localhost:8000/api/docs
  DB:       ~/.studentflow/studentflow.db
  Students: 20 active
```
