# Legal Connect — Project Work Tracker

> **Purpose:** This file is the living progress tracker for the Legal Connect project.
> At the start of every session, read this file to know exactly what is done and what remains.
> Update checkboxes and phase status after every completed step.

---

## 1. Project Overview

**Legal Connect — AI-Powered Legal Assistance Platform**
A final-year Computer Science Engineering project. A professional, responsive, secure, modular web
application connecting citizens with lawyers, featuring AI legal assistance, video consultations,
secure document sharing, and admin management.

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React.js, Vite, TypeScript, Tailwind CSS, React Router, TanStack Query, Zustand, Axios, React Hook Form, Zod, Recharts, Lucide React, Framer Motion, Vitest, React Testing Library |
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.0 (async), asyncmy, Alembic, JWT, bcrypt, FastAPI WebSockets, ReportLab, Pytest, HTTPX |
| Database | MySQL 8 (async SQLAlchemy + Alembic migrations) |
| Storage | Cloudinary (cloud only) |
| Real-time | FastAPI WebSockets (chat + notifications + WebRTC signaling) |
| Video | ZEGO Express Web SDK (v3.12, server-signed token04) |
| Maps | Leaflet + OpenStreetMap |
| Email | Resend / SMTP |
| AI | OpenAI-compatible API (provider-independent abstraction) |
| Hosting | Vercel (frontend), Render/Railway (backend) |

### Hard Restrictions
- ❌ NO Firebase anywhere
- ❌ NO Docker
- ❌ NO local MySQL / Redis / MinIO / etc. beyond a local development server
- ❌ NO MongoDB — migrated to MySQL; see revision `d4bf9214682c`
- ✅ Cloud services (managed MySQL, Cloudinary, Vercel, Render/Railway, Resend/SMTP, OpenAI)
- ✅ No hardcoded secrets — all via environment variables
- ✅ Optional services degrade gracefully when unconfigured (never crash)

---

## 2. Project Structure

```
legal-connect/
├── projectwork.md              ← THIS FILE (progress tracker)
├── AGENTS.md                   ← Project rules, build/test commands, conventions
├── README.md                   ← Full project documentation
├── .env.example                ← All environment variables (no real secrets)
├── .gitignore                  ← Ignore node_modules, venv, .env, dist, etc.
├── render.yaml                 ← Render deployment config (Phase 8)
│
├── frontend/
│   ├── src/
│   │   ├── app/                ← App.tsx, main.tsx, providers, router
│   │   ├── components/         ← Reusable shared UI components
│   │   ├── layouts/            ← PublicLayout, DashboardLayout
│   │   ├── pages/              ← Route-level page components
│   │   ├── features/           ← Feature modules (auth, lawyers, chat, ai, admin...)
│   │   ├── hooks/              ← Custom React hooks
│   │   ├── services/           ← API client + feature services
│   │   ├── stores/             ← Zustand stores (auth, theme...)
│   │   ├── types/              ← TypeScript type definitions
│   │   ├── utils/              ← Helper functions
│   │   └── lib/                ← Library setup (query client, etc.)
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── backend/
│   ├── app/
│   │   ├── main.py             ← FastAPI app entry point
│   │   ├── config.py           ← Pydantic settings (env vars)
│   │   ├── database.py         ← Motor async MongoDB client
│   │   ├── dependencies.py     ← DI (get_db, get_current_user, require_role)
│   │   ├── models/             ← MongoDB document models
│   │   ├── schemas/            ← Pydantic request/response schemas
│   │   ├── routers/            ← API route handlers
│   │   ├── services/           ← Business logic (auth, cloudinary, ai, pdf...)
│   │   ├── repositories/       ← Data-access layer
│   │   ├── middleware/         ← Rate limiting, security headers, etc.
│   │   ├── websocket/          ← Chat + signaling connection managers
│   │   ├── utils/              ← Helpers
│   │   └── tests/              ← Pytest test suite
│   ├── requirements.txt
│   ├── pytest.ini
│   └── .gitignore
│
├── scripts/
│   ├── seed_database.py        ← Demo data seeding (Phase 8)
│   └── create_admin.py         ← Secure admin creation (Phase 8)
│
└── docs/
    ├── implementation-plan.md  ← Phase-by-phase implementation detail
    ├── api.md                  ← API reference
    ├── architecture.md         ← System architecture (Mermaid)
    ├── security.md             ← Security design
    ├── deployment.md           ← Deployment guides
    ├── uml.md                  ← UML diagrams (Mermaid)
    ├── er-diagram.md           ← ER diagram (Mermaid)
    └── flowcharts.md           ← Flowcharts (Mermaid)
```

---

## 3. Development Phases

### Phase Status Legend
- ⬜ Not started
- 🔄 In progress
- ✅ Done

| # | Phase | Status |
|---|-------|--------|
| 1 | Project Foundation | ✅ |
| 2 | Authentication | ✅ |
| 3 | Core Platform (Profiles, Lawyers, Appointments, Reviews) | ✅ |
| 4 | Documents & Cloudinary | ✅ |
| 5 | Communication (Chat, WebSockets, WebRTC) | ✅ |
| 6 | AI Features + Maps | ✅ |
| 7 | Administration | ✅ |
| 8 | Quality, Testing & Deployment | ✅ |

---

## 4. Step-by-Step Progress Checklist

### Phase 1: Project Foundation

- [x] **Step 1.1** Create project directory, git init, projectwork.md, AGENTS.md, .env.example, .gitignore
- [x] **Step 1.2** Create full folder structure (frontend, backend, scripts, docs)
- [x] **Step 1.3** Backend: requirements.txt, venv, install deps
- [x] **Step 1.4** Backend: config.py, database.py, main.py, dependencies.py, health endpoint
- [x] **Step 1.5** Backend: verify uvicorn starts + /api/v1/health + /docs work
- [x] **Step 1.6** Frontend: Vite + React + TS init, install deps
- [x] **Step 1.7** Frontend: config (vite, tailwind), App.tsx, main.tsx, layouts, placeholder pages
- [x] **Step 1.8** Frontend: API client, auth store, types; verify npm run build
- [x] **Step 1.9** Docs scaffold (implementation-plan, architecture, api, security, deployment, README)

### Phase 2: Authentication

- [x] **Step 2.1** Backend: user models/schemas/repository + indexes
- [x] **Step 2.2** Backend: auth service (bcrypt, JWT, tokens) + email service
- [x] **Step 2.3** Backend: auth router (all 9 endpoints) + rate limiting
- [x] **Step 2.4** Backend: auth tests (registration, login, JWT, roles, reset)
- [x] **Step 2.5** Frontend: auth pages (login, register, forgot/reset, verify)
- [x] **Step 2.6** Frontend: protected routes, role guards, token interceptors, stores

### Phase 3: Core Platform

- [x] **Step 3.1** Backend: lawyer models/schemas/repository/service + search/filter
- [x] **Step 3.2** Backend: users router + profile management
- [x] **Step 3.3** Backend: appointments (book/cancel/reschedule/history, anti-double-booking)
- [x] **Step 3.4** Backend: reviews, notifications, complaints
- [x] **Step 3.5** Backend: legal categories + payments (demo)
- [x] **Step 3.6** Backend: core tests
- [x] **Step 3.7** Frontend: lawyer search + profile + booking flow
- [x] **Step 3.8** Frontend: citizen dashboard + profile + notifications + reviews
- [x] **Step 3.9** Frontend: lawyer dashboard + availability + appointment requests

> **Phase 3 status: COMPLETE.** Verification: backend pytest 45 passed; frontend build ✅, vitest 16 passed, eslint clean.
> Live Atlas smoke: health `mongodb: ok`, legal-categories 200 (12), lawyer search 200, lawyer profile PUT 200,
> complaint 201. Booking correctly returns 400 for unverified lawyers (requires ACTIVE verification status),
> verified flow covered by pytest.

### Phase 4: Documents

- [x] **Step 4.1** Backend: Cloudinary service (upload/delete/signed URL/validate)
- [x] **Step 4.2** Backend: document models/schemas/repository/router + sharing + audit
- [x] **Step 4.3** Backend: document tests
- [x] **Step 4.4** Frontend: document upload/list/viewer/share/download UI

> **Phase 4 status: COMPLETE.** Verification: backend pytest 64 passed; frontend build ✅, vitest 16 passed, eslint clean.
> Live Cloudinary smoke (real creds): upload OK (`legal-connect/...`), signed URL OK (`res.cloudinary.com/.../s--...--`), delete OK.
> Documents: multipart upload (max 25 MB), list (owned + shared), get, download (signed URL),
> share/revoke by email lookup (`GET /users/lookup`), owner-only delete, share notifications, audit logs
> (`audit_logs`). Graceful degradation → 503 when Cloudinary unconfigured.
> **Download note.** Signed-URL downloads now save the exact original bytes under the original
> filename/extension (blob fetch + `triggerDownload`) instead of Cloudinary's extension-less
> `public_id` — see §13.

### Phase 5: Communication

- [x] **Step 5.1** Backend: WebSocket chat manager + auth + persistence
- [x] **Step 5.2** Backend: conversations + messages routers (history, pagination)
- [x] **Step 5.3** Backend: WebRTC signaling (via WebSocket manager)
- [x] **Step 5.4** Frontend: chat interface (list, window, typing, receipts, files)
- [x] **Step 5.5** Frontend: WebRTC video call page

> **Phase 5 status: COMPLETE.** Verification: backend pytest full suite passes
> (incl. 10 new chat REST tests); frontend build ✅, vitest 16 passed, eslint clean.
> Live Atlas smoke: /api/v1/health mongodb ok; create_conversation 201,
> message history 200, send 200, mark-read 200, list with unread counts + last_message 200.
> Backend: FastAPI native WebSocket at /api/v1/ws (auth via ?token= access JWT),
> ChatService + conversation/message repos persisted in Mongo, WebRTC signaling
> (call-request/offer/answer/ice/decline/end) relayed between conversation peers.
> Frontend: ChatPage (conversation list + messages + typing + read receipts + auto re-connect
> socket + "New Chat" by email), VideoCallPage (RTCPeerConnection + STUN + graceful media
> fallback), routes /chat + /chat/video and /lawyer/chat + /lawyer/chat/video,
> "Message" button on lawyer profile auto-starts a chat via ?start=.
>
> **Video note.** Step 5.5's hand-rolled WebRTC `VideoCallPage` was later replaced by the ZEGO
> Express Web SDK (see §12); the routes stayed the same so nothing else upstream broke.

### Phase 6: AI Features + Maps

- [x] **Step 6.1** Backend: AI service abstraction (provider-independent, graceful failure)
- [x] **Step 6.2** Backend: AI router (chat, summarize, faq, predict, recommend, translate)
- [x] **Step 6.3** Backend: AI tests (unavailable behavior, validation)
- [x] **Step 6.4** Frontend: AI assistant, summarizer, category prediction, recommendation
- [x] **Step 6.5** Frontend: translation + voice (Web Speech / Speech Synthesis)
- [x] **Step 6.6** Frontend: Leaflet + OpenStreetMap nearby lawyers

> **Phase 6 status: COMPLETE.** Verification: backend pytest full suite passes
> (75 tests, incl. 9 new AI tests); frontend build ✅, vitest 16 passed, eslint clean.
> Backend: provider-independent AIService (httpx → OpenAI-compatible chat/completions,
> graceful 503 when OPENAI_API_KEY unset), /ai router with chat/summarize/faq/
> predict-category/recommend-lawyers/translate + GET /ai/nearby-lawyers; lawyer profile
> now stores optional latitude/longitude; LawyerRepository.list_with_geo returns mapped
> lawyers sorted by haversine distance. Frontend: AiAssistantPage (Assistant tab with
> chat + Web Speech voice input, Tools tab with summarizer/predictor/translator/
> recommender), NearbyLawyersMapPage (react-leaflet@4 + OpenStreetMap, browser geolocation,
> markers with popups); added /ai-assistant, /nearby-lawyers routes, sidebar + dashboard
> links; /emergency redirects to the map. AI not configured → clear 503 (no crash).

### Phase 7: Administration

- [x] **Step 7.1** Backend: admin router (dashboard, users, lawyers, verification, complaints, reports, analytics, audit)
- [x] **Step 7.2** Backend: admin tests
- [x] **Step 7.3** Frontend: admin dashboard + all admin pages (charts with Recharts)
- [x] **Step 7.4** Frontend: emergency legal help page

> **Phase 7 status: COMPLETE.** Verification: backend pytest full suite passes
> (88 tests, incl. 13 new admin tests); frontend build ✅, vitest 16 passed, eslint clean.
> Backend: admin router at `/api/v1/admin` — dashboard, users (list/status), lawyers
> (list/verification approve-reject-suspend), complaints (list/respond), analytics,
> audit-logs, reports/{users,lawyers,appointments,complaints,revenue}; all actions
> gated by `require_roles(ADMIN)` and recorded in `audit_logs`; suspend-self → 400;
> non-admin → 403; status/verification changes notify the target user.
> Frontend: AdminDashboard (recharts bar/pie charts from live analytics), AdminUsersPage,
> AdminLawyersPage, AdminComplaintsPage, AdminAuditLogsPage, AdminAnalyticsPage,
> AdminReportsPage; `/admin/*` routes under admin RoleRoute; admin nav sidebar updated.
> EmergencyHelpPage at `/emergency` (national helplines + nearby-lawyers link),
> replaces the earlier redirect.

> **Phase 7 LIVE verification (admin connectivity).** *Historical — performed against MongoDB Atlas
> before the MySQL migration.* Admin, dashboards, and APIs are connected to the real
> running site + MongoDB Atlas and verified end-to-end:
> - Single admin account: `admin@gmail.com` — **superseded**. That account was renamed during the
>   MySQL migration to `admin@legalconnect.com`; `admin@gmail.com` no longer authenticates.
> - Separate `/admin/login` page/route; public registration rejects `role:"admin"` (HTTP 400).
> - Backend enforces admin authz: citizen & lawyer tokens → 403 on all `/api/v1/admin/*`.
> - Lawyer verification live: Pankaj Tripathi (ACTIVE), Flow Lawyer (ACTIVE), Smoke Lawyer (REJECTED,
>   reason recorded); rejected lawyer not listed in public search. State persisted in Atlas at the time.
> - 2 complaints responded (RESOLVED + admin notes); users/lawyers reviewed (report-only).
> - 5 reports generated (users, lawyers, appointments, complaints, revenue) with PDF downloads.
> - Audit trail + user notifications confirmed in Atlas; session smoke accounts cleaned up.

### Phase 8: Quality, Testing & Deployment

- [x] **Step 8.1** Backend: PDF generation (ReportLab) + download endpoints
- [x] **Step 8.2** Seed data scripts (seed_database.py, create_admin.py)
- [x] **Step 8.3** Complete backend + frontend test suite (all passing)
- [x] **Step 8.4** Type checking + linting (frontend build, backend py_compile/mypy)
- [x] **Step 8.5** Error handling & UX polish (error boundary, toasts, skeletons, dark mode, mobile)
- [x] **Step 8.6** Complete documentation (README, docs/ with Mermaid diagrams)
- [x] **Step 8.7** Deployment config (render.yaml, Vercel, CORS, health)
- [x] **Step 8.8** Final verification against all acceptance criteria

---

## 5. Final Acceptance Criteria

The project is complete only when ALL of these pass:

- [x] Frontend starts successfully
- [x] Backend starts successfully
- [x] MySQL connection works (replaces the former MongoDB Atlas criterion)
- [x] Alembic migrations apply cleanly (`upgrade` → `downgrade` → `upgrade`)
- [x] Cloudinary upload + secure download work
- [x] Registration and login work
- [x] Role-based dashboards work
- [x] Lawyers can be verified by administrators
- [x] Users can search lawyers
- [x] Users can book appointments
- [x] Lawyers can accept or reject appointments
- [x] Users and lawyers can chat
- [x] Authorized users can join video consultations (ZEGO Express; server-signed token04 bound to the appointment room — 404/403/400/503 enforced backend-side)
- [x] AI features fail gracefully when not configured
- [x] PDF reports can be generated
- [x] Tests pass
- [x] API documentation is available
- [x] README contains complete setup instructions
- [ ] Project can be deployed without Docker (config ready: render.yaml + vercel.json; not yet deployed to a live URL)
- [x] No Firebase code or dependency exists
- [x] No secret is committed to the repository
- [x] Application works through a browser URL (local preview confirmed)

---

## 6. Environment & Accounts

### Verified Local Tools
| Tool | Version | Status |
|------|---------|--------|
| Node.js | 24.19.0 | ✅ |
| npm | 11.17.0 | ✅ |
| Python | 3.12.5 | ✅ |
| pip | 24.2 | ✅ |
| Git | 2.55.0 | ✅ |

### Cloud Accounts (user confirmed created)
| Service | Purpose | Config status |
|---------|---------|---------------|
| MySQL 8 (managed) | Database | ⬜ Set MYSQL_* in the host .env (deployment) |
| Cloudinary | File storage | ⬜ Add credentials to .env (Phase 3/4) |
| Resend/SMTP | Email | ⬜ Optional (Phase 2) |
| OpenAI | AI | ⬜ Optional (Phase 6) |
| Vercel | Frontend deploy | ⬜ Phase 8 |
| Render/Railway | Backend deploy | ⬜ Phase 8 |

---

## 9. Profile Address Field

`users.address` (nullable `TEXT`, revision `fef6641d722c`) stores a residential address on the
shared user record, so Citizen, Lawyer, and Admin all get it from the same profile form. It is
writable through `PATCH /api/v1/users/me`; `email` remains read-only there by design.

The profile page previously read `user.profile.city` / `user.profile.bio`, a nested shape the API
never returned, so saved values re-rendered blank on every reload. The frontend `User` type now
matches the flat API response and the form seeds from `GET /users/me`.

---

## 10. Profile Pictures

`users.profile_picture_url` (`VARCHAR(500)`) and `users.profile_picture_public_id`
(`VARCHAR(255)`), revision `a7c31e9b4d20`. Both nullable, on `users` rather than the lawyer-only
profile table, so Citizen, Lawyer, and Admin all share one pair of columns.

| Surface | How it works |
|---|---|
| Upload | `POST /api/v1/users/me/profile-picture`, multipart, reuses `get_document_storage` and `CloudinaryService.upload_bytes(resource_type="image")` |
| Remove | `DELETE /api/v1/users/me/profile-picture` (a dedicated route because `PATCH /users/me` drops `None`, so it can never clear a stored column) |
| Limits | 5 MB cap, `image/png` `image/jpeg` `image/webp`; empty 400, oversize 413, wrong type 422, Cloudinary down 503 |
| Replace | The previous asset is deleted via `storage.delete(old_public_id, "image")`, best-effort, after the new row is saved |
| Demo lawyers | Six flat vector portraits in `frontend/public/lawyers/`, assigned by `scripts/seed_database.py` |

The demo portraits are **illustrations, not photographs of real people**. Each is a distinct
geometric head-and-shoulders figure in business attire, so nothing depicts a real identifiable
individual.

`AppointmentResponse` gained `client_profile_picture_url`, `client_phone`, and `client_city`.
These are populated **only when the requester is the lawyer assigned to that appointment**
(`appointments.py::_to_response`) and are omitted from the payload entirely otherwise. A citizen
reading their own request gets no citizen-detail keys, and a non-participant is still rejected
with 403 by `_get_participant_appointment`. Nothing citizen-specific is added to the public
`GET /lawyers` response.

**Known limitation.** Profile pictures are stored as normal Cloudinary public-delivery assets, so
the API never hands a citizen's URL to anyone else, but the URL itself would work if it were
leaked or copy-pasted. Closing that fully needs `type="authenticated"` uploads plus the existing
`signed_url()` helper and a proxy route, which is more machinery than this change took on.

**Seed fix.** `scripts/seed_database.py` was not re-runnable: `reviews` has a unique constraint on
`(lawyer_id, reviewer_id)` and a re-run re-books the same lawyer/client pairs, so the insert raised
a duplicate-key error. It is now guarded with `find_by_user_and_lawyer`. The demo-portrait step only
fills an *empty* `profile_picture_url`, so a database seeded before this feature picks a portrait up
on the next run while a picture someone actually uploaded is never discarded.

---

## 11. Search, Voice, Earnings, Dashboard and Complaints

Five reported issues, fixed together. Two of the five reports named a symptom correctly but pointed
at the wrong cause, so each was traced to its real origin before anything was changed: earnings
*already* included confirmed appointments, and the voice feature *already* checked both
`SpeechRecognition` and `webkitSpeechRecognition`. No migration was required — all five reuse
existing tables, columns and endpoints.

**Lawyer search by name.** `q` filtered `bio`, `specializations` and `languages` only. A lawyer's
displayed name lives on `users.name`, and `_search_filters` (`lawyer_repository.py:221`) builds the
query from `lawyer_profiles` with no join, so the name was merged into the response *after*
filtering and could never affect it — searching a name returned "no lawyers found". Fixed with a
correlated `EXISTS` on `users.name`, reusing the idiom already used for category membership in the
same function. `EXISTS` rather than a join keeps `total` and `items` from disagreeing. No test had
ever passed `q`.

**AI voice input.** Two separate defects. First, the unsupported-browser warning read
`recognitionRef.current` during the first render, but the recognition instance is constructed in a
mount effect, so the first render always saw `null` and painted the warning; mutating a ref does not
re-render, so it never cleared. Now derived from state. `onerror` also discarded `event.error`, so a
denied microphone was indistinguishable from an unsupported browser; `no-speech`, `audio-capture`,
`not-allowed`, `service-not-allowed` and `network` now map to distinct messages, while `aborted` stays
silent because it is raised by the component's own cleanup. `start()` is guarded against
`InvalidStateError` on a double click, `rec.lang` is set from `navigator.language`, and the button
gained an accessible name, an `aria-pressed` state, and `disabled` when the API is absent.

Second, the recognition was configured `interimResults = false`, so it captured one finished sentence
and nothing appeared in the box while the user was still speaking. It is now `true`, so words stream
into the message box as they are spoken. The result handler was also reading `results[0]` only: with
interim results the browser *appends* chunks to the result list, so index 0 alone froze the box on the
first word and discarded the rest of the sentence. The handler now walks the entire list and separates
committed text (`isFinal`) from provisional text, keeping anything typed before the mic opened as a
prefix.

`continuous` deliberately stays `false`, because a pause is what ends the session and therefore what
triggers the auto-send. A finished utterance is submitted 1.2s after `onend`, so a trailing word can
still land. Since a pause *inside* one sentence splits it into two utterances, clicking the mic while
a send is queued cancels that send and resumes appending instead — this is the only way to keep talking
after a natural mid-sentence pause. An error also cancels a queued send, so a failed session can never
fire a question on its own. Because provisional text shares the input with typed text, a
user-initiated send is refused while listening, so a half-spoken sentence cannot be shipped by pressing
Enter. The send button also gained the `aria-label` it was missing.

**Lawyer earnings.** Split into **earned** (completed) and **projected** (confirmed but not yet
completed). Both surfaces read a single `useLawyerEarnings` hook under the one `['lawyer-earnings']`
key, so the earnings page and the dashboard cannot disagree. The actual defect behind "earnings only
update after Mark Complete" was that this key was never invalidated after an appointment changed
status — `LawyerAppointmentsPage` refreshed only `['lawyer-appointments']` — so the page served a
stale snapshot until a manual reload. A `hourly_rate` of 0 now prompts to set a rate instead of
rendering silent zero rows.

**Lawyer dashboard.** Rebuilt from a three-tile stub into six stat tiles (earned, projected, pending,
upcoming, completed, rating), six quick actions, inline accept and decline on pending requests,
upcoming and recently completed lists, recent activity from notifications, and a profile and
verification card that surfaces `rejection_reason`. Everything is derived client-side from endpoints
that already existed: no new routes and no chart library. Loading, error and content states are
explicit and match `AdminDashboard`, rather than rendering placeholder dashes on failure.

**Citizen complaints against a lawyer.** `POST /complaints` previously had **no role check and no
ownership check** — any authenticated user of any role could attach any `appointment_id`, including
one they had no part in. It is now citizen-only, and when `related_appointment_id` is supplied the
endpoint resolves the appointment (404 if absent) and requires the caller to be its `client_id`
(403 otherwise). This makes the "complaint against the wrong lawyer" case structurally impossible:
the lawyer is derived from the verified appointment and is never read from the request body. The
column already existed end to end across schema, router, repository and ORM and was simply never
sent by the frontend. On the profile page the option appears only when the citizen has an
appointment with that lawyer and is absent otherwise, with the most recent such appointment
attached. No new column and no migration.

### Verification

| Suite | Result |
|---|---|
| Backend pytest (real MySQL) | 149 passed |
| Frontend vitest | 81 passed |
| `npm run build` (`tsc -b`, strict) | clean |
| `npm run lint` | clean |

59 tests were added across these fixes (11 backend, 48 frontend). Where a test covers a defect rather
than new behaviour, it was confirmed to fail against the code it replaces: 4 for the name search, 1
for voice support detection, 2 for the complaint role check, 2 for complaint appointment ownership, the
dashboard error-state test, and 2 for live voice transcription. The remainder cover new behaviour, for
which there is no prior code to fail against.

### Known limitations

- `hourly_rate` is read once and applied to all history, so changing it retroactively revalues past
  earnings. Correcting this needs a per-appointment rate snapshot column.
- The dashboard, the earnings hook and the complaint eligibility gate each fetch `page_size: 100`
  with no pagination, so totals and eligibility silently truncate past that.
- The `payments` table is unreachable dead code: `payee_id` stores the *client*, so a lawyer always
  receives an empty list, and `POST /payments` is reachable only via `makePayment()`, which has no
  callers. Earnings are therefore derived from appointments, so no second earnings model was
  introduced.
- `frontend/src/test/setup.ts` gained an `Element.prototype.scrollTo` stub, because jsdom has no
  layout engine and the AI assistant page cannot otherwise be rendered in a test at all.
- Chrome's interim results are **provisional**: a word can appear and then be revised as recognition
  improves, so live text is a guess that stabilises. This is inherent to streaming transcription,
  not a defect in the handler.
- Auto-send cannot tell a mid-sentence pause from the end of a thought, so a question containing a
  natural pause may be submitted as two messages. Continuous listening was rejected as the fix
  because it removes the pause that triggers the auto-send. The remedy available to the user is to
  click the mic again during the 1.2s delay and keep speaking.
- **Not yet verified in a real browser.** The voice fix and the dashboard layout have been exercised
  only under jsdom and against MySQL.

---

## 12. ZEGO Video Consultations

Video calls moved from hand-rolled `RTCPeerConnection`/STUN to the **ZEGO Express Web SDK**
(`zego-express-engine-webrtc` v3.12). AuthN/A/Z stays server-side: the browser only receives a
signed token for the exact room it asked for, and the room itself is appointment-scoped.

**Backend**
- `app/utils/zego_token.py` — token04 generation (AES-CBC + base64, TTL 3600), signed with
  `ZEGO_APP_SECRET` and **bound to room `lc_<appointment_id>`**, so a token can't be replayed
  into any other room.
- `app/config.py` — `zego_app_id` / `zego_app_secret` / `is_zego_configured`; credentials only in
  gitignored `.env` (no `VITE_`-prefixed secret), `.env.example` documents them.
- `GET /api/v1/appointments/{id}/video-token` (`appointments.py`) reuses `_get_participant_appointment`:
  404 unknown ID → **403 non-participant** → **400 not CONFIRMED** → **503 ZEGO unconfigured**.
- 6 new tests in `backend/app/tests/test_video_token.py`.

**Frontend**
- `services/videoService.ts` (`getVideoToken`) and `VideoCallPage` rewritten on the ZEGO engine:
  `loginRoom` → `createZegoStream` → `startPublishingStream` / `startPlayingStream`, roomStream
  ADD/DELETE handling, roomState lost-connection banner, strict-mode-safe teardown
  (stopPublishing → destroyStream → logoutRoom → destroyEngine), mic/camera toggles via
  `muteMicrophone` / `mutePublishStreamVideo`, and 400/403/503/permission error screens.
- Legacy routes `/chat/video` and `/lawyer/chat/video` kept for backward compatibility; the Call
  button was removed from **ChatPage** (calls start from appointments instead).

**Personal appointment link**
- Shared route `/video-call/:appointmentId` added once under DashboardLayout (auth via
  ProtectedRoute; **authorization is enforced by the backend token endpoint**, not the route), with
  `?appointment=` query fallback for old links. `useParams` + peer-name lookup via the existing
  participant-authorized `GET /appointments/{id}` (derives client vs lawyer from `lawyer_id`),
  keeping `?peerName=` as a fast-path fallback.
- `VideoCallLink` component + **Copy link** button on CONFIRMED cards only (citizen and lawyer
  appointment pages); both "Video call" buttons now navigate to the unified `/video-call/{id}`.

**Audio hardening** (root causes of "no sound")
- Mic-permission pre-flight via `getUserMedia` with distinct messages for denied vs no device.
- After `createZegoStream`, verify `getAudioTracks()` is non-empty, show the active mic label, and
  listen for track `mute`/`unmute` (OS-level mic mute warning).
- Remote playback is explicit (`muted=false`, `volume=1`); the silently-swallowed `play()` rejection
  now drives a **"Tap to enable sound"** overlay so the browser's autoplay block is recoverable with
  a user gesture.
- Mic/cam toggles no-op until the stream exists; Back navigation falls back to the role's
  appointments page when history is empty (direct-link opens).

### Verification

| Suite | Result |
|---|---|
| Backend pytest (real MySQL) | 155 passed |
| Frontend vitest | 94 passed |
| `npm run build` (`tsc -b`, strict) | clean |
| `npm run lint` | clean |

---

## 13. Appointment Calendar & Document Downloads

Two reported issues, both frontend-only — no backend logic, schema, or storage changes.

**Appointment calendar.** `BookAppointmentSection` used a bare `datetime-local` input with no `min`,
so past bookable slots were selectable (the backend never validated `start_time` against now either).
It is now an in-app picker overlay: a date input with `min=today` (past dates disabled), and
hour / minute / AM-PM dropdowns whose options are disabled for today once that hour-minute-meridiem
combination has passed, plus an explicit **Done** button that validates the combined datetime is
future, commits the selection, and closes the picker (Cancel discards). The submit button also
refuses a now-past `start`. An AM/PM follow-up bug — all three selects were controlled by a single
`pickTime` state that only set when every part was present, so each selection snapped back to the
placeholder — was fixed by storing the three parts independently; `BookAppointmentSection.test.tsx`
(3 tests) locks this in.

**Document downloads.** Root cause reproduced live: the signed Cloudinary URL returned the **exact
original bytes** (verified `200`, correct `%PDF` body, `Access-Control-Allow-Origin: *`) but served
`Content-Disposition: attachment; filename="<public_id>"`. Because upload passes an explicit empty
`public_id`, Cloudinary stored a random, **extension-less name** (`file_lgxpyg`), so the browser
saved a validly-encoded file with no name/extension — opening as "blank". `fl_attachment`
transformations return `400` empty on this account (rejected as a fix). Resolved by fetching the
existing signed URL as a blob and saving it with the **original filename/extension from the DB**
via the existing `triggerDownload(blob, filename)` helper — applied to `DocumentsPage` (citizen and
lawyer share it) and to the admin's lawyer-proof view in `AdminLawyersPage`; `window.open(url)`
remains the fallback if the fetch fails. Upload, preview, share, revoke, delete and storage are
untouched.

### Verification

| Suite | Result |
|---|---|
| Backend pytest (real MySQL) | 155 passed (backend untouched) |
| Frontend vitest | 97 passed (12 files; +3 new picker tests) |
| `npm run build` (`tsc -b`, strict) | clean |
| `npm run lint` | clean |

---

## 14. Two-Way Admin Complaint Response

Complaints now carry **two independent admin replies**: one for the person who filed
the report (`complaints.user_id`) and one for the person reported
(`complaints.target_user_id`). Each reply is stored with its own timestamp, so a
recipient knows when the admin answered them.

**Backend**
- `complaints` gained `reporter_response`, `reporter_responded_at`,
  `reported_response`, `reported_responded_at` (revision `c7d8e9f0a1b2`, additive
  and idempotent; all four columns nullable, existing rows untouched).
- `ComplaintRepository.respond()` writes a direction only when a non-empty value is
  supplied and stamps that direction's timestamp, so a status-only update never
  clears an earlier reply.
- `PATCH /admin/complaints/{id}` (`AdminComplaintResponsePayload`) accepts
  `reporter_response` + `reported_response`, records an audit log, and notifies
  **each party separately** (notification `data.direction` is `"reporter"` for the
  complainant and `"reported"` for the reported party).
- Recipient isolation: `GET /complaints` strips the reported-side reply, and
  `GET /complaints/received` returns only the reported-side reply with the
  reporter's identity (name, email, `user_id`, `target_user_id`) never serialised.
- Both reporting directions are supported and proven: a citizen reporting a lawyer
  and a lawyer reporting a citizen (target always derived from an appointment or
  conversation the caller provably belongs to).

**Frontend**
- `AdminComplaintsPage` shows both stored replies, prefills the response form, and
  can save each direction independently (or just flip the status). The Respond
  form stays available even after a complaint is RESOLVED/REJECTED so an admin can
  add information or reopen a closed case.
- `ComplaintsPage` shows the admin reply on "My complaints" (`reporter_response`)
  and on "Complaints about me" (`reported_response`), both read fresh from the
  API on every load, so replies and notifications survive refresh and re-login.

### Verification

| Suite | Result |
|---|---|
| Backend pytest (real MySQL) | 199 passed (full suite) — includes two-way respond, per-party notifications, status-only preservation, admin access control (403/404) and recipient isolation in both directions |
| Frontend vitest | 139 passed (22 files) — includes 4 new `AdminComplaintsPage.test.tsx` + 3 new `ComplaintsPage.test.tsx` tests |
| `npm run build` (`tsc -b`, strict) | clean |
| `npm run lint` | clean |

## 15. Admin Revenue Ledger & INR Display

Admin Revenue is now defined as **₹10,000 per registered Citizen or Lawyer** plus
**5× the recorded lawyer earnings** from completed appointments, and every admin
surface shows it in Indian Rupees (`₹`, `en-IN` digit grouping).

**Backend**
- New `revenue_events` ledger (revision `3f774b2b69db`): one row per source with a
  unique `(event_type, reference_id)` key (`event_type` ∈ `registration` /
  `commission`), so recording is idempotent and revenue can never be double-counted.
- `RevenueRepository.record_idempotent()` uses MySQL `INSERT ... ON DUPLICATE KEY
  UPDATE` (no-op) plus the unique key; `total()` and `total_by_source()` read the sum.
- `POST /auth/register` records a ₹10,000 `registration` event for citizen and lawyer
  accounts (admins never generate revenue).
- `PATCH /appointments/{id}/complete` records a `commission` event = 5 ×
  (`hourly_rate` × appointment hours), skipping zero-rate lawyers.
- The migration backfills existing data idempotently (`INSERT IGNORE`): every
  citizen/lawyer becomes a registration event and every COMPLETED appointment with a
  positive rate becomes a commission event. Additive and safe to re-run.
- `GET /admin/dashboard.total_revenue`, `GET /admin/analytics.revenue_by_source`
  (replacing `revenue_by_status`) and the revenue report (`total_revenue` + `by_source`)
  now read the ledger. Payment rows are no longer treated as revenue.

**Frontend**
- Admin dashboard Revenue tile renders `₹` with `en-IN` grouping (e.g. `₹2,38,000`).
- Analytics "Revenue by source (INR)" chart shows `registration` and `commission`
  as `₹`-formatted, Indian-grouped bars.

### Verification

| Suite | Result |
|---|---|
| Backend pytest (real MySQL) | 204 passed (full suite) — includes 5 new `test_revenue.py` cases (registration fee, duplicate-register no-op, commission = 5×rate×hours, idempotent completion, zero-rate skips commission) |
| Frontend vitest | 141 passed (23 files) — includes 2 new `AdminDashboard.test.tsx` INR-format tests |
| `npm run build` (`tsc -b`, strict) | clean |
| `npm run lint` | clean |
| `alembic heads` | single head `3f774b2b69db`; dev DB backfilled to ₹2,38,000 (₹1,00,000 registration + ₹1,38,000 commission) |

---

## 16. Razorpay Consultation Payments

Real payments replace the old mock. A citizen pays a **server-computed** consultation fee
(`lawyer.hourly_rate × booked hours`) through Razorpay Checkout; the browser never sends an
amount, and every capture is HMAC-SHA256 signature-verified before it is recorded.

**Backend**
- New `payments` gateway columns (revision `b3c4d5e6f7a8`, additive, all nullable):
  `gateway_order_id`, `gateway_payment_id`, `gateway_signature`.
- `app/services/payment_gateway.py` — a dependency-free Razorpay client (existing `httpx` +
  stdlib `hmac`/`hashlib`): order creation over Basic auth, and constant-time verification of
  both the checkout signature and the `X-Razorpay-Signature` webhook header.
- `POST /payments/order` — participant + billable-status checks, computes the amount
  server-side, persists a PENDING payment, creates the order and returns the checkout payload
  (`key_id`, `amount_paise`, `order_id`, `reference`). `503` when unconfigured (graceful
  degradation), `502` on a gateway error, `409` when already paid.
- `POST /payments/verify` — checks the order matches, verifies the signature, marks PAID
  (idempotent) and notifies the lawyer.
- `POST /payments/webhook` — unauthenticated but signature-verified against the raw body;
  handles `payment.captured` / `order.paid` / `payment.failed`, ignores unknown orders.
- `GET /payments/appointment/{id}` — the caller's latest payment for an appointment.
- Removed the mock `POST /payments` that wrote PAID from a client-supplied amount;
  `GET /payments` and `GET /payments/{id}/receipt` are unchanged.

**Frontend**
- `services/paymentService.ts` (`createPaymentOrder` / `verifyPayment` /
  `getAppointmentPayment`) and `lib/razorpay.ts` (lazy Checkout loader).
- `CitizenAppointmentsPage` shows **Pay consultation fee** on confirmed/completed unpaid
  appointments, a **Paid** badge once captured, and surfaces gateway errors inline.
- About / FAQ / Terms rewritten: the platform now *does* process payments via Razorpay.

**Config** — `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` / `RAZORPAY_WEBHOOK_SECRET`
(`.env.example`, `render.yaml`; the webhook URL is
`{BACKEND_URL}/api/v1/payments/webhook`).

### Verification

| Suite | Result |
|---|---|
| Backend pytest (real MySQL) | 229 passed (full suite) — includes new `test_payments.py` (server-side amount, client-supplied amount ignored, non-participant 403, unconfirmed 409, signature verify + idempotency, bad signature 400, webhook capture, bad webhook 400) |
| Frontend vitest | 154 passed (25 files) — includes 4 new payment-flow tests |
| `npm run build` (`tsc -b`, strict) | clean |
| `npm run lint` | clean |
| `alembic heads` | single head `b3c4d5e6f7a8` |

---

## 17. Cloud Deployment Preparation (Aiven + Render + Netlify)

Prepared the app for public deployment: a managed **Aiven for MySQL** database
(Free tier, Bangalore) preserving all existing data, a **Render** web service for the
FastAPI backend and **Netlify** for the React frontend. Local development is
unchanged; every code change is additive.

**Backend**
- MySQL TLS for managed providers: `Settings.mysql_ssl_required`, `mysql_ssl_ca`,
  `mysql_skip_database_creation` and a `mysql_connect_args` property that builds an
  `ssl.SSLContext` (CA-verified when a CA PEM is supplied, otherwise encrypted
  without verification); `app/db/session.py` passes these to both async engines and
  can skip the `CREATE DATABASE` bootstrap.
- Migration `c9e8f1a2b3d4_add_is_demo_to_lawyer_profiles` (revises `b3c4d5e6f7a8`,
  additive) adds `lawyer_profiles.is_demo BOOLEAN NOT NULL DEFAULT 0` and backfills
  the five seed demo lawyers by email; surfaced through the model, serializer and
  lawyer schema.
- `scripts/rotate_demo_credentials.py` (`--dry-run`, `--include-citizens`) rotates the
  shared `DemoPass123` password after go-live.

**Frontend**
- `is_demo?: boolean` added to the lawyer type; a **Demo** badge shown in
  `LawyerListPage` and `LawyerProfilePage`.

**Config / docs**
- `.env.example` documents `MYSQL_SSL_REQUIRED` / `MYSQL_SSL_CA` /
  `MYSQL_SKIP_DATABASE_CREATION`; `render.yaml` sets the Aiven TLS flags and now
  prompts for `MYSQL_HOST` / `MYSQL_PORT` (non-standard Aiven port); `docs/deployment.md`
  rewritten around Aiven + Render + Netlify with the TLS and demo-credential runbook.

### Verification

| Item | Result |
|---|---|
| Backend pytest (real MySQL) | 229 passed |
| Frontend vitest | 154 passed |
| `npm run build` / `npm run lint` | clean |
| `alembic heads` | single head `c9e8f1a2b3d4` |
| Data migration | verified backup (SHA-256 `0B18BE89...`) restored to a scratch DB (21 tables, 0 mismatches, head `c9e8f1a2b3d4`, 5 demo flags), then imported into Aiven over TLS; verified 21 tables, head `c9e8f1a2b3d4`, 5 demo lawyers, 13 users |

**Status / next**
- Commit `5695202` pushed to `origin/master`.
- Aiven DB live and populated. Render backend created but still needs env values
  (`MYSQL_HOST` / `MYSQL_PORT=17359`, reset password, TLS flags, strong
  `SECRET_KEY` / `JWT_SECRET_KEY`, and a non-localhost `CORS_ORIGINS` / `FRONTEND_URL`
  for the Netlify site - the app refuses to boot in production while CORS is
  localhost). Netlify frontend not yet deployed.
- Pending: rotate the exposed Aiven password, `scripts/create_admin.py`,
  `scripts/rotate_demo_credentials.py`, Razorpay webhook
  `{BACKEND_URL}/api/v1/payments/webhook`.

---

*Last updated: Deployment preparation is underway — the app now supports Aiven's
TLS-encrypted MySQL (`MYSQL_SSL_REQUIRED` / `MYSQL_SSL_CA` / `MYSQL_SKIP_DATABASE_CREATION`),
an `is_demo` flag marks the five seed lawyers (`revision c9e8f1a2b3d4`) with a Demo badge,
and `render.yaml` / `docs/deployment.md` now target Aiven + Render + Netlify. The verified
backup was imported into Aiven over TLS (21 tables, head `c9e8f1a2b3d4`, 5 demo lawyers,
13 users) and commit `5695202` pushed; backend pytest 229 passed, frontend vitest 154
passed, build and lint clean. Earlier: Consultation payments now run end-to-end through Razorpay — the amount is
computed server-side from the lawyer's hourly rate and booked hours, the citizen completes
Checkout on confirmed/completed appointments, and both the checkout signature and the webhook
are HMAC-verified before a payment is marked PAID (`revision b3c4d5e6f7a8` adds three nullable
gateway columns to `payments`). Backend pytest 229 passed, frontend vitest 154 passed, build and
lint clean. Earlier: Admin revenue is now a ledger-backed total — ₹10,000 per registered
citizen/lawyer plus 5× completed-appointment earnings (`revision 3f774b2b69db`, a
`revenue_events` table with a unique `(event_type, reference_id)` key, idempotent
`INSERT ... ON DUPLICATE KEY UPDATE` recording and an `INSERT IGNORE` backfill of
existing users and completed appointments) — surfaced in Indian Rupees on the admin
dashboard, analytics ("Revenue by source") and revenue report. The dev database
backfills to ₹2,38,000 (₹1,00,000 registration + ₹1,38,000 commission). Backend pytest
204 passed, frontend vitest 141 passed, build and lint clean. Earlier: Admin complaints
now carry two independent replies (one for the reporter,
one for the reported party), each stored with its own timestamp (`revision c7d8e9f0a1b2`),
delivered only to its intended recipient (`GET /complaints` vs `GET /complaints/received`),
with per-party notifications and an audit log; the admin Respond form stays available on
closed complaints. Backend pytest 199 passed, frontend vitest 139 passed, build and lint
clean. Earlier: video consultations now run on the ZEGO Express Web SDK with a personal,
appointment-scoped link (`/video-call/:appointmentId`, Copy link on CONFIRMED cards) and an audio
pass — mic-permission pre-flight, audio-track/system-mute checks, and an autoplay "enable sound"
overlay — backed by a token endpoint that enforces participant (403), CONFIRMED (400) and
configured-ZEGO (503) checks server-side. Also that round: the booking calendar blocks past dates
and past times today with an explicit Done/AM-PM picker (regression-tested), and document downloads
save the exact original bytes under the original filename/extension instead of Cloudinary's
extension-less public_id. No schema changes; backend pytest 155 passed, frontend vitest 97 passed,
build and lint clean. Prior work: AI voice input now streams live (`interimResults = true`) and
auto-sends 1.2s after a pause, with the result handler fixed to walk every chunk instead of only the
first; clicking the mic during the delay cancels the pending send. Also in that round: lawyer name
search now matches `users.name`, earnings split into earned and projected with the stale
`['lawyer-earnings']` cache now invalidated on status change, lawyer dashboard rebuilt, and
`POST /complaints` given the role and appointment-ownership checks it previously lacked plus a gated
citizen reporting form. No migration. Backend pytest 149 passed, frontend vitest 81 passed, build
and lint clean. Earlier: profile pictures (revision `a7c31e9b4d20`: shared `users` columns,
Cloudinary upload/remove routes with old-asset cleanup, six fictional demo lawyer portraits,
lawyer-only citizen details on appointment responses, re-runnable seed script, 138 backend and 33
frontend tests plus 17 live checks against real Cloudinary and MySQL), MongoDB to MySQL migration
(17 tables, revision `d4bf9214682c`, legacy ObjectId-compatible `CHAR(24)` IDs preserved), profile
address field (`fef6641d722c`), and six real public pages replacing the Under Construction
placeholders. Single admin `admin@legalconnect.com` via `/admin/login`.*
