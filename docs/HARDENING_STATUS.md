# Hardening Status & User-Action Checklist

This document tracks what the hardening pass has completed in code, and what
still requires you (the operator) to do outside the code before onboarding a
real institution.

## What was done in code

### Part A — code-level fixes
- [x] Removed `backend/create_admin.py` and `backend/seed_data.py` (stale,
      neither set `institution_id` and would fail on the current schema).
- [x] Removed committed SQLite dev DBs (`timetable.db`, `test_timetable.db`).
- [x] Deleted `PROJECT_EXPLAINED.md`; replaced `README.md` with a concise
      operational guide.
- [x] [backend/app/main.py](backend/app/main.py): removed `Base.metadata.create_all`
      from lifespan — Alembic migrations are the single source of truth. Added
      HSTS, CSP, Permissions-Policy, tightened CORS to explicit methods and
      headers. Disabled docs at `/api/docs` in production.
- [x] [backend/app/core/scheduler.py](backend/app/core/scheduler.py): removed
      hardcoded period-time docstring; `get_institution_config` now raises if
      no `ScheduleConfig` is present instead of silently falling back to
      hardcoded defaults; tenant-scoped slot deletion.
- [x] [backend/app/core/llm_agent.py](backend/app/core/llm_agent.py): replaced
      the "nvapi-" key-prefix sniffing with explicit `LLM_PROVIDER` dispatch
      (see `settings.resolved_llm_base_url`). Removed the ALL-CAPS threat
      prompt, replaced with a plain instruction. System prompt now includes
      `period_times` when configured.
- [x] [backend/app/config.py](backend/app/config.py): added `LLM_PROVIDER`,
      `LLM_API_KEY`, `LLM_BASE_URL`, `DB_SSL_MODE`, SMTP_*, `ENVIRONMENT`.
      Startup validation refuses to run in production with weak secrets.
- [x] Tenant-isolation leak in
      [backend/app/api/faculty.py](backend/app/api/faculty.py#L83-L89):
      `get_faculty_schedule` now filters `TimetableSlot` by `institution_id`.

### Part B — secrets hygiene
- [x] [.env.example](.env.example) committed with every required var.
- [x] [.gitignore](.gitignore) now excludes `.env.production`, `.env.staging`,
      `firebase-credentials*.json`, `service-account*.json`, `backups/`.
- [x] Startup validation refuses to boot in production with `JWT_SECRET <32
      chars`, missing LLM key, wildcard CORS, or `DEBUG=True`.

### Part C — infrastructure & security
- [x] [backend/Dockerfile](backend/Dockerfile): non-root `app` user, built-in
      `HEALTHCHECK` hitting `/health/live`, removed unused MySQL client libs.
- [x] `/health/live` and `/health/ready` endpoints (ready checks DB + Redis).
- [x] Per-endpoint rate limits:
      - `/api/auth/token`, `/api/auth/google`: 10/min
      - `/api/chat`: 20/min
      - Global default: `RATE_LIMIT_PER_MINUTE * 10` per IP per minute.
- [x] Data export endpoint:
      [`GET /api/institution/export`](backend/app/api/institution.py) returns a
      ZIP of CSVs, scoped to the caller's institution.
- [x] Data deletion endpoint:
      [`DELETE /api/institution`](backend/app/api/institution.py) hard-deletes
      all tenant-scoped data, requires `?confirm_slug=<slug>` footgun guard,
      marks the institution inactive and retains `AuditLog` for compliance.
- [x] Multi-tenant isolation test suite:
      [backend/tests/test_tenant_isolation.py](backend/tests/test_tenant_isolation.py).
      Covers list, get, update, delete across faculty / subject / room / batch,
      and verifies the export endpoint is scoped. Add cases here for every new
      CRUD endpoint.
- [x] nginx reverse-proxy template:
      [deploy/nginx/timetable.conf](deploy/nginx/timetable.conf) with HSTS,
      HTTP→HTTPS redirect, tiered rate limits, SSE-safe buffering.
- [x] Backup + restore scripts: [scripts/backup-db.sh](scripts/backup-db.sh),
      [scripts/restore-db.sh](scripts/restore-db.sh). Cron-ready, S3-optional,
      refuses to restore over a populated DB without `--force`.
- [x] Runbook: [docs/RUNBOOK.md](docs/RUNBOOK.md).

### Tests
- `19/19 passing` as of this hardening pass (14 pre-existing + 5 new tenant
  isolation tests).

---

## What still requires YOUR action

These cannot be done by changing code. Do them before a real institution
touches the system.

### Secrets you must rotate yourself
- [ ] **NVIDIA / OpenAI / Anthropic API key**: whichever key was committed to
      git in the past must be considered permanently compromised. Rotate it in
      the provider console, then set the new value as `LLM_API_KEY` in
      production `.env`.
- [ ] **JWT_SECRET**: generate a fresh 32-byte secret with
      `openssl rand -hex 32`.
- [ ] **POSTGRES_PASSWORD**: generate a new 24+ char random password.
- [ ] **Firebase service account**: if a service account JSON was ever used,
      generate a new one in the Firebase console and delete the old one.

### Git history
- [ ] Run `trufflehog filesystem --directory .` to confirm no live secrets.
- [ ] If any old commit contains a real key, purge it with `git filter-repo`
      (destructive — coordinate with anyone who has a clone). The key is still
      considered compromised and must be rotated regardless.

### Infrastructure (do on a real VPS)
- [ ] Provision HTTPS with Let's Encrypt / certbot; point nginx at the certs
      referenced in [deploy/nginx/timetable.conf](deploy/nginx/timetable.conf).
- [ ] Replace `yourdomain.com` in the nginx template with the real domain.
- [ ] Open only ports 22, 80, 443 on the host firewall. DB and Redis must
      remain on the Docker network.
- [ ] Enable `DB_SSL_MODE=require` and use a managed Postgres with encryption
      at rest (DO Managed DB / RDS).
- [ ] Install cron entry for `scripts/backup-db.sh` (nightly, 02:00 UTC).
- [ ] Verify a restore once: use `scripts/restore-db.sh` against a scratch
      container.
- [ ] Set up an S3 bucket for offsite backups; set `S3_BUCKET` in the env
      used by cron.
- [ ] Connect Sentry: create a project, set `SENTRY_DSN` in `.env`, import
      `sentry_sdk` in `app/main.py` (tiny code change — not done here because
      it requires an account).
- [ ] Point UptimeRobot at `https://yourdomain.com/health/ready` every 5min.

### Legal / compliance
- [ ] Publish Terms of Service and Privacy Policy. A lawyer is ideal; Termly
      (~$10/month) is a fast path. Link both in the app footer.
- [ ] Prepare a Data Processing Agreement template. Any institution will ask.
- [ ] Decide and document data retention — how long timetable slots, audit
      logs, and deleted-institution stubs are kept.

### Pilot onboarding
- [ ] Choose one friendly institution to pilot with for 4–6 weeks free. Fix
      whatever breaks before signing a second.

---

## Verification checklist (from the original plan, status now)

| # | Check | Status |
|---|-------|--------|
| 1 | No secrets in git history | **TODO** — run trufflehog |
| 2 | All secrets via env, startup fails if missing in prod | ✓ |
| 3 | `docker compose -f docker-compose.prod.yml up --build` boots on fresh VPS | **TODO** — verify on your server |
| 4 | HTTPS with valid Let's Encrypt cert, HTTP→HTTPS | **TODO** — requires VPS |
| 5 | Security headers present | ✓ (app-layer + nginx) |
| 6 | CORS whitelists production domain only | ✓ (validation refuses wildcard in prod) |
| 7 | Multi-tenant isolation pytest passes | ✓ (`test_tenant_isolation.py`) |
| 8 | Rate limits enforced per endpoint | ✓ |
| 9 | DB backup runs nightly, one restore tested | **TODO** — cron + first restore |
| 10 | Sentry receives a test error | **TODO** — requires account |
| 11 | UptimeRobot monitoring /health/ready | **TODO** |
| 12 | ToS + Privacy Policy linked in footer | **TODO** |
| 13 | Data export endpoint works | ✓ |
| 14 | Data deletion endpoint works | ✓ |
| 15 | RUNBOOK.md complete | ✓ |
| 16 | Invite flow works with real Firebase in staging | **TODO** — requires staging env |
| 17 | LLM fallback shows clear error | ✓ (see `run_agent`) |
| 18 | Existing tests pass + new isolation tests | ✓ (19/19) |
| 19 | Coverage >80% on tenant-scoped paths | **TODO** — run `pytest --cov` |
| 20 | Pilot institution identified | **TODO** |
