# Legal Connect — Implementation Plan

This document details the phase-by-phase implementation of the Legal Connect platform.
The canonical progress tracker lives in `projectwork.md` at the repository root.

---

## Phase 1: Project Foundation ✅

Goal: A runnable skeleton with both apps, health check, base UI, and API client.

- Folder structure (frontend, backend, scripts, docs)
- Git initialization and `.gitignore` / `.env.example`
- `AGENTS.md` and `projectwork.md`
- FastAPI backend: `config.py`, `database.py`, `dependencies.py`, `main.py`, `/api/v1/health`
- React frontend: Vite + TS + Tailwind, layouts, placeholder pages, API client, auth store
- Documentation scaffold

**Status: COMPLETE**
- Backend starts, `/api/v1/health` returns 200, `/docs` and `/redoc` serve.
- Frontend `npm run build`, `npm test`, `npm run lint` all pass.
- MongoDB configured flag reports `not_configured` gracefully when env missing.

---

## Phase 2: Authentication

- User model/schema/repository + indexes (unique email, role, status)
- Auth service: bcrypt hashing, JWT access + refresh, reset tokens
- Email service (Resend/SMTP) with graceful fallback
- Router endpoints:
  - POST `/api/v1/auth/register`
  - POST `/api/v1/auth/login`
  - POST `/api/v1/auth/logout`
  - POST `/api/v1/auth/refresh`
  - POST `/api/v1/auth/forgot-password`
  - POST `/api/v1/auth/reset-password`
  - POST `/api/v1/auth/verify-email`
  - GET `/api/v1/auth/me`
  - PATCH `/api/v1/auth/change-password`
- Rate limiting for login/reset
- Frontend: auth pages, JWT interceptors, protected + role-based routes, auth store

---

## Phase 3: Core Platform

- User profiles, lawyer profiles, lawyer search + filters (category, city, experience, language, fees, rating, availability)
- Appointments: book, cancel, reschedule, history, statuses, anti-double-booking
- Reviews, notifications, complaints
- Legal categories + demo payments
- Frontend: lawyer search/directory/profile, booking flow, citizen + lawyer dashboards

---

## Phase 4: Documents (Cloudinary)

- CloudinaryService: upload, delete, signed URLs, validation
- Document model/router: upload, private download, sharing, revocation, audit logs
- Frontend: upload/list/viewer/share/download UI

---

## Phase 5: Communication

- WebSocket chat (JWT auth, persistence, typing, receipts, online status, files, reconnect)
- Conversations + messages routers with pagination
- WebRTC signaling via WebSockets
- Frontend: chat UI, video call page

---

## Phase 6: AI Features + Maps

- Provider-independent AIService (graceful failure)
- AI endpoints: chat, summarize, faq, predict-category, recommend-lawyers, translate
- Frontend: AI assistant, summarizer, category prediction, recommendation, translation, voice
- Leaflet + OpenStreetMap nearby-lawyer map

---

## Phase 7: Administration

- Admin router: dashboard, users, lawyers, verification, complaints, reports, analytics, audit logs
- Audit recording for admin actions
- Frontend: admin dashboard and all admin pages (Recharts)

---

## Phase 8: Quality, Testing & Deployment

- PDF generation (ReportLab) + protected download endpoints
- Seed data scripts
- Full backend + frontend test suites
- Type/lint/fix, UX polish (toasts, skeletons, dark mode, mobile)
- Full documentation with Mermaid diagrams
- Deployment config (render.yaml, Vercel, CORS, health)
- Final acceptance verification
