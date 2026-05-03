# Pilot Readiness Report — Timetable-LLM

This document summarizes the hardening work completed to bring Timetable-LLM to pilot-ready status for a single-institution deployment.

## 1. Architectural Hardening
- **Asynchronous Processing**: Timetable generation is now handled asynchronously via Celery and Redis. The UI polls for task status, preventing timeouts during long-running LLM/CP-SAT operations.
- **Transactional Integrity**: Critical flows (Google Login, User Creation) are wrapped in database transactions to ensure consistency.
- **Sentry Integration**: Production error monitoring is wired into both FastAPI and Celery workers for real-time observability.

## 2. Security & RBAC
- **HttpOnly Cookies**: Authentication tokens are stored in secure, HttpOnly cookies to mitigate XSS risks.
- **JWT Claims**: Custom claims (`institution_id`, `role`) are embedded in JWTs to reduce database load and enforce multi-tenant isolation at the token level.
- **Frontend Gating**: Admin-only sections and pages are protected by a `<RoleGuard>` component and client-side redirection.
- **SMTP Notifications**: A secure SMTP-based email system is implemented for invitations and password resets.

## 3. Operations & Maintenance
- **Audit Log Retention**: Automated daily cleanup of audit logs older than 365 days (configurable) via Celery Beat.
- **Database Performance**: New indexes on `audit_logs(created_at)` and optimized query patterns.
- **Constraint Engine**: Added faculty daily workload caps and unavailable slot enforcement to the CP-SAT scheduler.

## 4. Verification Results
- **Backend Tests**: All 22 tests passing with 65% code coverage.
- **Static Analysis**: Ruff linting passed (zero errors).
- **Frontend Build**: Production build successful (`next build`).

## 5. Deployment Pre-flight Checklist
- [ ] Configure `SENTRY_DSN` in production environment.
- [ ] Set `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`.
- [ ] Verify Redis connectivity for Celery.
- [ ] Apply final Alembic migrations to production DB.

---
*Date: April 24, 2026*
*Status: Ready for Pilot Deployment*
