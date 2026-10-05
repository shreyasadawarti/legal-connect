# Legal Connect — Security

## Principles

1. **No secrets in source.** All credentials come from environment variables in `.env`
   (gitignored). Only `.env.example` (with placeholder values) is committed.
2. **Layered auth.** Every protected route/endpoint verifies all of:
   - Authentication (valid JWT)
   - Account status (active)
   - Required role (user / lawyer / admin)
   - Resource ownership
   - Appointment participation (chat/consultation) where applicable
   - Document sharing permissions where applicable
3. **Defense in depth for storage.** Cloudinary files stay private; downloads use
   time-limited signed URLs. Cloudinary secrets never reach the frontend.
4. **Optional-service resilience.** Unconfigured services (AI, email, Cloudinary)
   return clear messages and never crash.

## Controls

- **Passwords**: bcrypt (or Argon2) hashing, never stored in plain text.
- **JWTs**: HS256, short-lived access tokens + refresh tokens.
- **CORS**: restricted to configured origins.
- **Rate limiting**: applied to login and password-reset endpoints.
- **Input validation**: Pydantic schemas; parameterised SQLAlchemy queries (no string-built SQL).
- **XSS**: React escapes rendered content; no `dangerouslySetInnerHTML`.
- **Files**: validate MIME type, extension, and size; safe IDs; private storage.
- **Audit**: important admin and sensitive document actions recorded in `audit_logs`.
- **HTTPS**: production deployments use HTTPS-ready configuration.

## Secrets checklist

- [ ] `.env` never committed
- [ ] No Cloudinary/AI/SMTP secrets in frontend bundle
- [ ] Account/lawyer/document ownership checks enforced
- [ ] Rotate any leaked credential immediately
