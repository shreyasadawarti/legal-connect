# AGENTS.md — Legal Connect Project Rules

This file defines the architecture, build commands, test commands, coding conventions, and project
rules for the **Legal Connect – AI-Powered Legal Assistance Platform**.

Any agent or contributor working on this repository MUST read and follow these rules.

---

## Project Overview

Legal Connect is a full-stack platform connecting citizens with lawyers. It includes AI legal
assistance, WebRTC video consultations, secure Cloudinary document sharing, real-time chat, and an
admin dashboard for lawyer verification.

- **Frontend:** `frontend/` (React + Vite + TypeScript + Tailwind)
- **Backend:** `backend/` (Python 3.12 + FastAPI + MongoDB Atlas)
- **Progress tracker:** `projectwork.md` — read at session start to know what is done/remaining

---

## Architecture

### Request flow
`React Frontend` → `FastAPI Backend` → `MongoDB Atlas` / `Cloudinary` / `OpenAI-compatible API`

- The frontend NEVER talks directly to MongoDB, Cloudinary, or external AI providers.
- All business logic lives in `backend/app/services/`.
- Data access lives in `backend/app/repositories/`.
- HTTP handlers live in `backend/app/routers/` (all under `/api/v1`).

### Backend layer order
`routers` → `schemas` → `services` → `repositories` → `models` (MongoDB)

---

## Non-Negotiable Rules

1. **NO Firebase** — ever. No code, no dependency.
2. **NO Docker** — no Dockerfiles, no docker-compose, no container config.
3. **NO local database/storage** — MongoDB Atlas & Cloudinary cloud services only.
4. **NO hardcoded secrets** — all credentials via environment variables (`.env`, gitignored).
5. **Never commit secrets** — `.env` is gitignored; provide only `.env.example`.
6. **Graceful degradation** — optional services (AI, email, Cloudinary) must never crash the app
   when unconfigured; show a clear configuration message instead.
7. **Frontend-only env vars** must be prefixed with `VITE_`.
8. **Do not rewrite working code** unnecessarily.
9. Work in small, verifiable phases; run tests/build after each phase; fix errors before proceeding.
10. All protected routes/endpoints verify: authentication, account status, role, ownership,
    appointment/document participation where applicable.

---

## Build & Run Commands

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
npm run build
```

---

## Test Commands

### Backend (Pytest)
```bash
cd backend
venv\Scripts\activate
python -m pytest
python -m pytest -v
```

### Frontend (Vitest)
```bash
cd frontend
npm test
npm run test:watch
```

---

## Verification Commands (run after each phase)

1. `cd backend && python -m pytest` — backend tests pass
2. `cd frontend && npm test` — frontend tests pass
3. `cd frontend && npm run build` — type check + production build succeeds
4. Start backend — `/api/v1/health` returns 200, `/docs` loads
5. Start frontend — Vite dev server starts without errors

---

## Coding Conventions

### General
- No unnecessary comments in code (comments only where genuinely clarifying).
- Follow existing patterns — mimic surrounding code style.

### Backend (Python)
- Type hints everywhere.
- Pydantic schemas for all request/response validation.
- Use Motor (async) for MongoDB.
- Routers are thin; business logic in services.
- Use `from app...` absolute imports.

### Frontend (TypeScript)
- TypeScript strict mode.
- Functional components with hooks (no class components unless required).
- Use the existing UI primitives in `src/components/`.
- Feature code lives in `src/features/<feature>/`.
- Use existing stores/services — do not duplicate state logic.

---

## Roles

Three roles:
1. **Citizen / User** — search lawyers, book appointments, chat, upload documents, AI features.
2. **Lawyer** — manage availability, accept/reject appointments, chat, share documents, earnings.
   New lawyers are `PENDING_VERIFICATION` until an admin approves them (no verified badge).
3. **Administrator** — verify lawyers, manage users, complaints, reports, analytics, audit logs.
   All important admin actions recorded in `audit_logs`.

---

## Notes
- See `docs/` for in-depth architecture, API, security, and deployment documentation.
- See `projectwork.md` for the phase-by-phase progress checklist.
