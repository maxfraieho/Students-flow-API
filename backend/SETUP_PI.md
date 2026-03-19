# StudentFlow FastAPI Backend — Raspberry Pi Setup Guide

## 1. System requirements

```bash
sudo apt update && sudo apt install -y \
  python3 python3-pip python3-venv git \
  python3-secretstorage libdbus-1-dev
```

## 2. Clone / copy the backend to the Pi

Copy the `artifacts/fastapi-backend/` directory to your Pi, e.g.:
```bash
scp -r artifacts/fastapi-backend pi@raspberrypi.local:~/studentflow-api
```

## 3. Create a Python venv and install dependencies

```bash
cd ~/studentflow-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Headless keyring note:** On a headless Pi without GNOME Keyring, run:
> ```bash
> pip install keyrings.cryptfile
> ```
> Then set the backend before running the app:
> ```bash
> export PYTHON_KEYRING_BACKEND=keyrings.cryptfile.cryptfile.CryptFileKeyring
> ```

## 4. First run — initialise the database

```bash
cd ~/studentflow-api
source .venv/bin/activate
python run.py
```

The DB is created automatically at `~/.studentflow/studentflow.db`.  
Default settings (canonical path, branch name, etc.) are inserted on first boot.

## 5. Store credentials in the OS keyring

Use the API after the server is running, or call this helper script once:

```bash
python - <<'EOF'
from app.security.vault import SecretVault
v = SecretVault()
# GitHub PAT for student account
v.set("studentflow:github:student-username:acc-uuid8", "YOUR_GITHUB_TOKEN_HERE")
print("Stored OK")
EOF
```

You can also POST to `/api/credentials` once the server is running:
```bash
curl -X POST http://localhost:8050/api/credentials \
  -H "Content-Type: application/json" \
  -d '{"account_id":"<account_uuid>","secret_kind":"pat","value":"YOUR_GITHUB_TOKEN_HERE"}'
```

## 6. Configure the cloudflared tunnel

```bash
cloudflared tunnel create studentflow
cloudflared tunnel route dns studentflow studentflow.yourdomain.com
```

Config file (`~/.cloudflared/config.yml`):
```yaml
tunnel: <TUNNEL_ID>
credentials-file: /home/pi/.cloudflared/<TUNNEL_ID>.json
ingress:
  - hostname: studentflow.yourdomain.com
    service: http://localhost:8050
  - service: http_status:404
```

Start the tunnel:
```bash
cloudflared tunnel run studentflow
```

## 7. Run as a systemd service

Create `/etc/systemd/system/studentflow-api.service`:
```ini
[Unit]
Description=StudentFlow FastAPI Backend
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/studentflow-api
Environment=PYTHON_KEYRING_BACKEND=keyrings.cryptfile.cryptfile.CryptFileKeyring
ExecStart=/home/pi/studentflow-api/.venv/bin/python run.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable studentflow-api
sudo systemctl start studentflow-api
sudo systemctl status studentflow-api
```

## 8. API endpoint reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/students` | List all students |
| GET | `/api/students/active` | Get active student |
| GET | `/api/students/next` | Get next queued student |
| POST | `/api/students` | Create student |
| PUT | `/api/students/{id}` | Update student |
| POST | `/api/students/{id}/activate` | Set student as active |
| GET | `/api/accounts` | List accounts |
| POST | `/api/accounts` | Create account |
| POST | `/api/credentials` | Store credential in keyring |
| PUT | `/api/credentials/{id}/rotate` | Rotate credential |
| GET | `/api/repositories` | List repositories |
| POST | `/api/repositories` | Register repository |
| POST | `/api/sync/current` | Sync active student's repo |
| POST | `/api/sync/student/{id}` | Sync specific student's repo |
| GET | `/api/sync/jobs` | List sync jobs |
| POST | `/api/handoff` | Execute handoff to next student |
| GET | `/api/handoff/events` | List handoff history |
| GET | `/api/prompts` | List all prompts |
| POST | `/api/prompts` | Create and push prompt file |
| POST | `/api/prompts/{id}/retry` | Retry failed push |
| GET | `/api/audit` | Query activity log |
| GET | `/api/settings` | List all settings |
| PUT | `/api/settings/{key}` | Update setting |
| GET | `/api/docs` | Interactive Swagger UI |

## 9. Curl smoke test (after server starts)

```bash
# Health check
curl http://localhost:8050/api/health

# Create a student
curl -s -X POST http://localhost:8050/api/students \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Bohdan Marchenko","status":"active","queue_position":1,"student_number":1}'

# List students
curl http://localhost:8050/api/students

# Check active student
curl http://localhost:8050/api/students/active
```

## 10. Adding real student data

Once the API is running, use the Swagger UI at `http://localhost:8050/api/docs` or the curl commands above to:

1. **POST /api/students** — create each student record
2. **POST /api/accounts** — create a GitHub/GitLab account for each student
3. **POST /api/credentials** — store the PAT/token in the keyring
4. **POST /api/repositories** — register the local clone path + remote URL
5. **PUT /api/settings/canonical_repo_path** — set the path to your canonical bare repo
