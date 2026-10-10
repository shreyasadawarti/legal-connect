# Legal Connect — Deployment Runbook

Production topology:

```
Vercel (React/Vite SPA)  ──HTTPS/WS──►  Render (FastAPI + uvicorn)
        │                                      │
        │                                      ├── Railway MySQL 8 (asyncmy)
        │                                      ├── Cloudinary (documents/images)
        │                                      ├── OpenAI-compatible API (AI)
        │                                      ├── SMTP / Resend (email)
        │                                      └── Razorpay (payments)
        └──► Razorpay Checkout (browser, opened by the SPA)
```

```mermaid
flowchart LR
    V[Vercel - React SPA] --> B[Render - FastAPI]
    B --> M[(MySQL 8)]
    B --> C[(Cloudinary)]
    B --> AI[OpenAI-compatible API]
    B --> E[(Resend / SMTP)]
    V -->|Leaflet| O[OpenStreetMap]
    V --> RAZ[Razorpay Checkout]
```

The repo already contains `render.yaml` (backend Blueprint) and
`frontend/vercel.json` (Vite SPA rewrites). This runbook is the order of
operations. Everything marked **(secret)** must be filled in from the provider
dashboard — `render.yaml` declares them with `sync: false` on purpose so no
secret is committed.

> Run every local command from the repository root unless stated otherwise.

---

## 0. Prerequisites

- A GitHub repo containing this project (Render and Vercel deploy from Git).
- Accounts: [Railway](https://railway.app), [Render](https://render.com),
  [Vercel](https://vercel.com), [Razorpay](https://dashboard.razorpay.com),
  and (for documents) [Cloudinary](https://cloudinary.com).
- Generate two strong secrets (≥32 random chars) for `SECRET_KEY` and
  `JWT_SECRET_KEY`, e.g. `python -c "import secrets;print(secrets.token_urlsafe(48))"`.
  The app **refuses to start in production** with the default/weak values, a
  localhost MySQL host, or localhost-only CORS (`validate_production_settings`).

---

## Phase B — MySQL on Railway

1. Railway → **New Project → Provision MySQL**.
2. Open the MySQL service → **Variables** / **Connect** tab and copy the
   **public** host and port (Render is an external network; the private
   `*.railway.internal` host will not resolve).
3. Map them to the backend's variable names (Railway names may differ):

   | Railway value | Backend env var |
   |---|---|
   | `MYSQLHOST` / public host | `MYSQL_HOST` |
   | `MYSQLPORT` / public port | `MYSQL_PORT` |
   | `MYSQLUSER` | `MYSQL_USER` |
   | `MYSQLPASSWORD` | `MYSQL_PASSWORD` |
   | `MYSQLDATABASE` | `MYSQL_DATABASE` (`legal_connect`) |

4. Do **not** create tables by hand. The backend start command runs
   `alembic upgrade head`, and `AUTO_CREATE_TABLES=false` in production.

Keep these values handy for Phase C and for creating the admin account (Phase F).

---

## Phase C — Backend on Render

1. Render → **New → Blueprint**, pick the repo. Render reads `render.yaml` and
   creates the `legal-connect-backend` web service (`rootDir: backend`,
   `healthCheckPath: /api/v1/health`, free plan). `backend/.python-version` pins
   Python **3.12** for the build — Render's current default is 3.14, which breaks
   the pinned `asyncmy`/`SQLAlchemy` versions, so keep that file in the repo.
2. Fill in every **(secret)** variable on the service (Render prompts for each
   `sync: false` key). Values applied automatically: `APP_ENV=production`,
   `MYSQL_DATABASE=legal_connect`, `MYSQL_PORT=3306`, `AUTO_CREATE_TABLES=false`,
   `AI_PROVIDER=openai`, `SMTP_PORT=587`, `SMTP_USE_TLS=true`,
   `GEOCODING_PROVIDER=nominatim`, `WEBRTC_STUN_SERVER`, `CLOUDINARY_FOLDER`.

   | Variable | Value / source |
   |---|---|
   | `SECRET_KEY` **(secret)** | strong random string |
   | `JWT_SECRET_KEY` **(secret)** | strong random string (different from above) |
   | `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` **(secret)** | from Phase B |
   | `FRONTEND_URL` **(secret)** | the Vercel URL (add now as a placeholder, fix after Phase D, e.g. `https://legal-connect.vercel.app`) |
   | `BACKEND_URL` **(secret)** | this service's URL, e.g. `https://legal-connect-backend.onrender.com` |
   | `CORS_ORIGINS` **(secret)** | the Vercel origin(s), comma-separated — must **not** be localhost |
   | `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` **(secret)** | Cloudinary dashboard |
   | `OPENAI_API_KEY` / `OPENAI_MODEL` / `OPENAI_BASE_URL` **(secret)** | AI provider (optional — AI degrades gracefully) |
   | `SMTP_HOST` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM_EMAIL` **(secret)** | email provider, or set `RESEND_API_KEY` instead |
   | `ZEGO_APP_ID` / `ZEGO_APP_SECRET` **(secret)** | ZEGOCLOUD console (video) |
   | `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` **(secret)** | Razorpay dashboard (Phase E) |
   | `RAZORPAY_WEBHOOK_SECRET` **(secret)** | the secret you choose in Phase E |
   | `GOOGLE_MAPS_API_KEY`, `WEBRTC_TURN_*` **(secret)** | optional |

   > Email matters: unverified accounts cannot log in. Configure SMTP **or**
   > `RESEND_API_KEY` before inviting users.
3. Deploy. Confirm:
   - Build runs `pip install -r requirements.txt`.
   - Start runs `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
   - `https://<backend>/api/v1/health` returns `{"status":"ok",...}`.
   - `https://<backend>/docs` loads.
4. If the service crashes on boot, read the log — the most likely cause is a
   guard from `validate_production_settings` (weak secret, localhost MySQL, or
   localhost-only CORS).

---

## Phase D — Frontend on Vercel

1. Vercel → **New Project**, import the repo, set **Root Directory = `frontend`**
   (the framework preset is detected from `frontend/vercel.json`, which rewrites
   all routes to `index.html`).
2. Add environment variables (Vite exposes only `VITE_`-prefixed vars at build
   time — set them before/at first build):

   | Variable | Value |
   |---|---|
   | `VITE_API_URL` **(required)** | `https://<backend-host>/api/v1` |
   | `VITE_SOCKET_URL` (optional) | `wss://<backend-host>` |

   With `VITE_API_URL` set, `SOCKET_URL` is derived automatically as the same
   host over `wss://`; the app connects to `<SOCKET_URL>/api/v1/ws`. Do **not**
   set `VITE_API_URL` to `/api/v1` — the Vercel rewrite sends unknown paths to
   `index.html`, so a relative API base would not reach Render.

3. Deploy, then open the Vercel URL. If the SPA cannot reach the API, it is
   almost always CORS: go back to Phase C and set `CORS_ORIGINS` to the exact
   Vercel origin (scheme + host, no trailing slash) and redeploy the backend.

---

## Phase E — Razorpay (payments) and ZEGO (video)

1. Razorpay dashboard → **Account & Settings → API Keys** → generate keys for
   the mode you want (Test keys first). Put them in the Render service:
   `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`.
2. **Account & Settings → Webhooks → Add New Webhook**:
   - URL: `https://<backend-host>/api/v1/payments/webhook`
   - Secret: any strong string → paste into `RAZORPAY_WEBHOOK_SECRET` on Render.
   - Active events: `payment.captured`, `payment.failed`, `order.paid`.
3. ZEGOCLOUD console → Project Information → copy AppID and ServerSecret into
   `ZEGO_APP_ID` / `ZEGO_APP_SECRET` (the ServerSecret is server-side only and
   is never sent to the browser).
4. Redeploy the backend so the new values take effect.

---

## Phase F — Create the administrator account

Admins are never created through the public registration endpoint. Run the
script locally against the **production** MySQL, with the Railway credentials in
the environment:

```powershell
# PowerShell, from the repo root
$env:MYSQL_HOST="<railway-public-host>"
$env:MYSQL_PORT="<railway-public-port>"
$env:MYSQL_USER="<railway-user>"
$env:MYSQL_PASSWORD="<railway-password>"
$env:MYSQL_DATABASE="legal_connect"

python scripts/create_admin.py --name "Administrator" --email admin@yourdomain.com --password "ChangeMe123!"
```

Alternatively run the same command in the Render **Shell** tab (the service
already has the env vars). The script runs `alembic upgrade head` itself, so it
is safe even on a fresh database.

Log in at `/admin/login` with that email/password, then change the password.

---

## Post-deploy verification checklist

- [ ] `GET https://<backend>/api/v1/health` → `status: ok` (not `degraded`).
- [ ] `/docs` loads; `/` returns the app banner.
- [ ] Register a citizen → verification email arrives → verify → log in.
- [ ] Register a lawyer → upload a verification document → admin approves it.
- [ ] Citizen books an appointment; lawyer confirms it.
- [ ] Citizen pays via Razorpay Checkout; payment shows **Paid**; the lawyer
      receives a notification and the receipt PDF downloads.
- [ ] Razorpay dashboard shows the **webhook** as delivered (HTTP 200).
- [ ] Chat sends a message in real time (WebSocket reaches `wss://<backend>/api/v1/ws`).
- [ ] Video call joins a ZEGO room.
- [ ] Admin dashboard shows INR revenue.

---

## Schema migrations

Production schema is owned by Alembic:

```bash
# apply all migrations (Render runs this automatically on every deploy)
alembic upgrade head
```

Additive migrations only; never edit tables by hand. Current chain head after
this work: `b3c4d5e6f7a8`.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Backend won't boot / Render says "exited" | `validate_production_settings` guard: weak `SECRET_KEY`/`JWT_SECRET_KEY`, `MYSQL_HOST` is localhost, or `CORS_ORIGINS` is localhost-only. Fix the env var and redeploy. |
| Frontend network errors in console | `CORS_ORIGINS` on the backend must contain the exact Vercel origin; or `VITE_API_URL` is wrong/relative. |
| `MYSQL ... can't connect` on Render | Use Railway's **public** host/port, not `*.railway.internal`. |
| WebSocket fails to connect | `VITE_SOCKET_URL`/`VITE_API_URL` host wrong, or backend offline; check the browser's WS URL is `wss://<backend>/api/v1/ws?token=...`. |
| Registration emails never arrive | SMTP/Resend not configured; unverified accounts cannot log in. |
| Payment **Pay** button shows a config error | `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` missing → endpoint returns 503 on purpose. |
| Webhook 400 | `RAZORPAY_WEBHOOK_SECRET` on Render does not match the Razorpay webhook secret. |
| 401 immediately after login | Tokens are per-session; ensure the backend clock/`JWT_*` settings are consistent and `JWT_SECRET_KEY` did not change mid-session. |

---

## Local development (for reference)

```powershell
# Backend
cd backend
python -m venv venv; .\venv\Scripts\activate
pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Copy `.env.example` to `.env` (repo root) and fill in local values. Run tests
with `cd backend; python -m pytest` and `cd frontend; npm test`.
