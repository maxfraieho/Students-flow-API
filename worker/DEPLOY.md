# StudentFlow API Gateway — Setup Guide

## Prerequisites

- A [Cloudflare account](https://dash.cloudflare.com/sign-up) (free tier is enough)
- Node.js 18+ installed on your local machine
- `cloudflared` running on your Raspberry Pi and a tunnel URL ready

---

## 1. Install Wrangler CLI

```bash
npm install -g wrangler
```

Log in to your Cloudflare account:

```bash
wrangler login
```

---

## 2. Configure `wrangler.toml`

Open `wrangler.toml` and replace the placeholder values:

| Variable | What to put there |
|---|---|
| `TUNNEL_URL` | The public HTTPS URL of your `cloudflared` tunnel, e.g. `https://abc123.trycloudflare.com` |
| `FRONTEND_URL` | The origin of your Lovable.dev app, e.g. `https://my-app.lovable.app` |

> **Do NOT put `OPERATOR_TOKEN` in `wrangler.toml`** — it must be stored as a secret (see step 3).

---

## 3. Add the `OPERATOR_TOKEN` Secret

This is the pre-shared key your React frontend will send in the `Authorization: Bearer <token>` header. Choose a long, random string (e.g. 32+ characters).

**Option A — Wrangler CLI (recommended):**

```bash
wrangler secret put OPERATOR_TOKEN
```

Wrangler will prompt you to enter the secret value interactively. It is encrypted and stored in Cloudflare — it never appears in plain text anywhere.

**Option B — Cloudflare Dashboard:**

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com)
2. Navigate to **Workers & Pages → studentflow-api-gateway**
3. Open **Settings → Variables**
4. Scroll to **Secret Variables** and click **Add variable**
5. Name: `OPERATOR_TOKEN`, Value: your chosen secret token
6. Click **Encrypt** then **Save**

---

## 4. Deploy the Worker

```bash
wrangler deploy
```

Cloudflare will print the Worker's public URL, e.g.:
```
https://studentflow-api-gateway.<your-subdomain>.workers.dev
```

This is the URL your React frontend should send API requests to.

**Live worker URL:**
```
https://studentflow-api-gateway.maxfraieho.workers.dev
```

---

## 5. Test the Worker

**Test that auth is enforced (should return 401):**

```bash
curl -i https://studentflow-api-gateway.<your-subdomain>.workers.dev/api/healthz
```

**Test with correct token (should return the backend response):**

```bash
curl -i \
  -H "Authorization: Bearer YOUR_OPERATOR_TOKEN" \
  https://studentflow-api-gateway.<your-subdomain>.workers.dev/api/healthz
```

**Test with wrong token (should return 401):**

```bash
curl -i \
  -H "Authorization: Bearer wrongtoken" \
  https://studentflow-api-gateway.<your-subdomain>.workers.dev/api/healthz
```

**Test when the Pi is offline (should return 502):**

Stop `cloudflared` on your Pi, then send any authenticated request — the Worker will return:
```json
{ "error": "Bad Gateway", "detail": "Could not reach the backend. The Raspberry Pi may be offline or the tunnel is down." }
```

---

## 6. Frontend Integration

In your Lovable.dev React app, make API calls like this:

```javascript
const WORKER_URL = "https://studentflow-api-gateway.<your-subdomain>.workers.dev";
const OPERATOR_TOKEN = "YOUR_OPERATOR_TOKEN"; // store this in your frontend's env vars

const response = await fetch(`${WORKER_URL}/api/students`, {
  method: "GET",
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${OPERATOR_TOKEN}`,
  },
});
```

> Store `OPERATOR_TOKEN` in your Lovable.dev project's environment variables (Settings → Environment Variables), not hardcoded in source code.

---

## Architecture Overview

```
React (Lovable.dev)
  │
  │  Authorization: Bearer <OPERATOR_TOKEN>
  ▼
Cloudflare Worker (studentflow-api-gateway)
  │  ✓ Validates token against env.OPERATOR_TOKEN
  │  ✓ Strips Authorization header (Pi never sees the token)
  │  ✓ Rewrites URL to TUNNEL_URL
  │  ✓ Appends CORS headers to response
  ▼
cloudflared tunnel  (public HTTPS ↔ Raspberry Pi local port)
  ▼
FastAPI server (Raspberry Pi, localhost)
```
