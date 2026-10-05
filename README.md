# Legal Connect — AI-Powered Legal Assistance Platform

A final-year Computer Science Engineering project. A professional, responsive, secure, modular web
application that connects citizens with verified lawyers, featuring AI-powered legal assistance,
video consultations, secure Cloudinary document sharing, real-time chat, and an admin dashboard.

> **Important:** This project uses **no Firebase and no Docker**. All services are cloud-hosted
> (MongoDB Atlas, Cloudinary, Vercel, Render/Railway). Optional services degrade gracefully when
> not configured.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, Vite, TypeScript, Tailwind CSS, React Router, TanStack Query, Zustand, Axios, React Hook Form, Zod, Recharts, Lucide, Framer Motion, Vitest |
| Backend | Python 3.12, FastAPI, Pydantic, Motor/PyMongo, JWT, bcrypt, WebSockets, ReportLab, Pytest, HTTPX |
| Database | MongoDB Atlas |
| Storage | Cloudinary (private, signed URLs) |
| Maps | Leaflet + OpenStreetMap |
| Email | Resend / SMTP |
| AI | OpenAI-compatible API (provider-independent) |

---

## Prerequisites

- Node.js 20+ and npm
- Python 3.12+
- Git
- Cloud accounts: MongoDB Atlas, Cloudinary (Resend/OpenAI optional)

---

## Quick Start (local development)

### 1. Configure environment

Copy `.env.example` to `.env` in the project root and fill in your values
(especially `MONGODB_URI`, `CLOUDINARY_*`).

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`. Docs: `/docs`, health: `/api/v1/health`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`. The Vite dev server proxies `/api` to the backend.

---

## Testing

```bash
# Backend
cd backend && venv\Scripts\activate && python -m pytest

# Frontend
cd frontend && npm test
```

---

## Verification Commands

```bash
# Backend
python -m pytest                  # tests
python -m uvicorn app.main:app    # run + check /api/v1/health

# Frontend
npm run build                     # type check + production build
npm test                          # unit tests
npm run lint                      # lint
npm run dev                       # run dev server
```

---

## Project Structure

See `projectwork.md` for the full structure and the phase-by-phase progress checklist.

- `frontend/` — React SPA
- `backend/` — FastAPI service
- `scripts/` — seed and admin-creation scripts
- `docs/` — architecture, API, security, deployment, UML/ER/flowchart docs

---

## Documentation

- `docs/architecture.md` — system architecture
- `docs/api.md` — API reference
- `docs/security.md` — security design
- `docs/deployment.md` — deployment guides (Vercel + Render/Railway)
- `docs/uml.md`, `docs/er-diagram.md`, `docs/flowcharts.md` — diagrams
- `docs/implementation-plan.md` — phase-by-phase plan

---

## Roles

- **Citizen / User** — search lawyers, book appointments, chat, documents, AI features.
- **Lawyer** — availability, appointment requests, chat, documents, earnings (pending verification until admin approval).
- **Administrator** — lawyer verification, user management, complaints, reports, analytics, audit logs.

---

## License

For academic / final-year project demonstration purposes.
