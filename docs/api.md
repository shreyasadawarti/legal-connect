# Legal Connect — API Reference

Base path: `/api/v1`

Interactive docs: `/docs` (Swagger UI) and `/redoc` (ReDoc).

## Conventions

- All JSON bodies/payloads validated with Pydantic schemas.
- Authentication: `Authorization: Bearer <access_token>` (JWT).
- Error responses return `{ "detail": "message" }`.
- Role-based access control enforced on routers.
- Optional external services (AI, email, Cloudinary) return clear configuration errors
  (`503`) rather than crashing when unconfigured.

## Endpoint Categories

| Router | Prefix | Key endpoints |
|--------|--------|---------------|
| Health | `/health` | `GET /api/v1/health` |
| Auth | `/auth` | register, login, logout, refresh, forgot/reset password, verify-email, me, change-password |
| Users | `/users` | profile management |
| Lawyers | `/lawyers` | search, list, detail, availability |
| Appointments | `/appointments` | book, cancel, reschedule, history (`/my`) |
| Documents | `/documents` | upload, download, share, revoke |
| Conversations | `/conversations` | list, create |
| Messages | `/messages` | history, pagination |
| Reviews | `/reviews` | create, list |
| Notifications | `/notifications` | list, mark read |
| Complaints | `/complaints` | create, list, respond (admin) |
| Payments | `/payments` | demo payment workflow |
| Admin | `/admin` | dashboard, users, lawyers, verification, appointments, complaints, reports, analytics, audit-logs, settings |
| AI | `/ai` | chat, summarize, faq, predict-category, recommend-lawyers, translate |
| Reports | `/reports` | PDF generation |

### Example: Auth flows

```text
POST /api/v1/auth/register    { name, email, password, ... }
POST /api/v1/auth/login       { email, password }  → { access_token, refresh_token }
GET  /api/v1/auth/me          Authorization: Bearer <token>
```

### Example: Profile management

Self-service only. The target user always comes from the access token, so there is no way to
address another account. Both endpoints return the same flat object, matching the `users` row.

```text
GET   /api/v1/users/me
PATCH /api/v1/users/me
```

Writable fields on `PATCH /users/me`: `name`, `phone`, `city`, `address`, `bio`,
`preferred_language`. All are optional; only the keys present in the request body are written.
An empty string clears a field — omitted or `null` keys are left untouched.

`email` is deliberately **not** writable here. It is the login identifier, and changing it would
require a uniqueness check plus a decision about re-verification, so it stays read-only. The
frontend renders it disabled.

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | `CHAR(24)` ObjectId-compatible |
| `name` | string | 1–120 chars |
| `email` | string | unique, read-only |
| `phone` | string \| null | max 20 |
| `city` | string \| null | max 120 |
| `address` | string \| null | max 500, added in revision `fef6641d722c` |
| `bio` | string \| null | max 2000 |
| `preferred_language` | string \| null | max 20; stored only — the UI is not translated |
| `role` | enum | `user` \| `lawyer` \| `admin` |
| `status` | enum | `ACTIVE` \| `SUSPENDED` \| `DEACTIVATED` |

Lawyer-only professional fields (practice areas, hourly rate, availability, verification status)
live on `lawyer_profiles` and are managed separately through `/lawyers/me/*`.

### Example: Booking

```text
POST /api/v1/appointments     { lawyer_id, scheduled_start, scheduled_end, consultation_type, ... }
GET  /api/v1/appointments/my  → list current user's appointments
```

*(Full request/response schemas are generated live in Swagger UI at `/docs`.)*
