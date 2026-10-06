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
| Video | WebRTC + STUN/TURN |
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
- [x] Authorized users can join video consultations
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

**AI voice input.** The unsupported-browser warning read `recognitionRef.current` during the first
render, but the recognition instance is constructed in a mount effect, so the first render always
saw `null` and painted the warning; mutating a ref does not re-render, so it never cleared. Now
derived from state. `onerror` also discarded `event.error`, so a denied microphone was
indistinguishable from an unsupported browser; `no-speech`, `audio-capture`, `not-allowed`,
`service-not-allowed` and `network` now map to distinct messages, while `aborted` stays silent
because it is raised by the component's own cleanup. `start()` is guarded against
`InvalidStateError` on a double click, `rec.lang` is set from `navigator.language`, and the button
gained an accessible name, an `aria-pressed` state, and `disabled` when the API is absent.

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
| Frontend vitest | 69 passed |
| `npm run build` (`tsc -b`, strict) | clean |
| `npm run lint` | clean |

47 tests were added (11 backend, 36 frontend). Where a test covers a defect rather than new
behaviour, it was confirmed to fail against the code it replaces: 4 for the name search, 1 for
voice support detection, 2 for the complaint role check, 2 for complaint appointment ownership, and
the dashboard error-state test. The remainder cover new behaviour, for which there is no prior code
to fail against.

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
- **Not yet verified in a real browser.** The voice fix and the dashboard layout have been exercised
  only under jsdom and against MySQL.

---

*Last updated: Search, voice, earnings, dashboard and complaints fixed: lawyer name search now
matches `users.name`, AI voice input support detection and permission errors corrected, earnings
split into earned and projected with the stale `['lawyer-earnings']` cache now invalidated on
status change, lawyer dashboard rebuilt, and `POST /complaints` given the role and
appointment-ownership checks it previously lacked plus a gated citizen reporting form. No
migration. Backend pytest 149 passed, frontend vitest 69 passed, build and lint clean. Prior work:
profile pictures (revision `a7c31e9b4d20`: shared `users` columns, Cloudinary upload/remove routes
with old-asset cleanup, six fictional demo lawyer portraits, lawyer-only citizen details on
appointment responses, re-runnable seed script, 138 backend and 33 frontend tests plus 17 live
checks against real Cloudinary and MySQL), MongoDB to MySQL migration (17 tables, revision
`d4bf9214682c`, legacy ObjectId-compatible `CHAR(24)` IDs preserved), profile address field
(`fef6641d722c`), and six real public pages replacing the Under Construction placeholders. Single
admin `admin@legalconnect.com` via `/admin/login`.*
