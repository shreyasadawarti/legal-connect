# Legal Connect — Architecture

## System Overview

```mermaid
flowchart LR
    subgraph Browser
        R[React SPA]
    end
    subgraph Vercel
        R
    end
    subgraph Render / Railway
        API[FastAPI Backend]
        WS[WebSocket Servers]
    end
    R -->|HTTP/REST /api/v1| API
    R -->|WebSocket /ws| WS
    API --> M[(MySQL 8)]
    API --> C[(Cloudinary)]
    API --> AI[OpenAI-compatible API]
    API --> EM[(Resend / SMTP)]
    R -->|Leaflet| OSM[OpenStreetMap]
```

## Layers (Backend)

```
routers  →  schemas  →  services  →  repositories  →  models (SQLAlchemy)
   │                                  │
   └── HTTP / WS + auth + RBAC        └── data access + indexes
```

- **Routers**: HTTP endpoints under `/api/v1`, WebSocket endpoints under `/ws`.
- **Schemas**: Pydantic request/response models (validation).
- **Services**: business logic (auth, appointments, cloudinary, ai, pdf, email).
- **Repositories**: MySQL data access via async SQLAlchemy (`AsyncSession`).
- **Models**: document shapes / collections.

## Frontend Structure

- **State**: Zustand (auth, theme); TanStack Query for server state.
- **HTTP**: Axios instance with JWT attach + refresh interception.
- **Routing**: React Router; protected + role-based route guards.
- **Forms**: React Hook Form + Zod.
- **Styling**: Tailwind CSS (light/dark mode), Framer Motion for animations, Recharts for analytics.

## Security Boundaries

- Frontend never talks directly to MySQL, Cloudinary, or external AI providers.
- All such calls pass through the authenticated backend.
- Cloudinary files stored privately; downloads use time-limited signed URLs.
- Never expose Cloudinary/AI secrets to the React application.
