# Timetable LLM

Multi-tenant SaaS for automated college/school/coaching-center timetable
generation. Natural-language chat interface + constraint solver + configurable
schedule per institution.

## Features

- AI chat interface backed by LangChain tool-calling
- OR-Tools CP-SAT constraint solver for conflict-free scheduling
- Per-institution `ScheduleConfig` (working days, periods, period times)
- Firebase Google sign-in + JWT session cookies
- Invite-based user onboarding
- PDF / Excel export
- Audit logging
- Celery + Redis for async tasks
- Docker Compose for dev and prod

## Quick Start (Docker)

```bash
cp .env.example .env          # fill in real values — see below
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend:  http://localhost:8000
- API docs: http://localhost:8000/api/docs (disabled in production)

## Local Development

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Tests

```bash
cd backend
pytest -v
```

## Required Environment Variables

All secrets must come from the environment. See `.env.example`.

| Variable | Purpose |
|----------|---------|
| `ENVIRONMENT` | `development` \| `staging` \| `production` |
| `DEBUG` | `False` in production |
| `JWT_SECRET` | ≥32-char random string (`openssl rand -hex 32`) |
| `DATABASE_URL` or `DB_*` | Postgres connection |
| `DB_SSL_MODE` | `require` in production |
| `REDIS_URL` | Redis connection |
| `LLM_PROVIDER` | `openai` \| `nvidia` \| `anthropic` |
| `LLM_API_KEY` | LLM provider API key |
| `LLM_BASE_URL` | Override base URL (optional) |
| `LLM_MODEL` | Model identifier |
| `FIREBASE_PROJECT_ID` | Firebase project ID |
| `ALLOWED_ORIGINS` | Comma-separated CORS whitelist |
| `RATE_LIMIT_PER_MINUTE` | Default rate limit |
| `SMTP_*` | For invite emails |

In production (`ENVIRONMENT=production`), the app refuses to start if
`JWT_SECRET` is weak, `LLM_API_KEY` is missing, `DEBUG` is on, or
`ALLOWED_ORIGINS` contains `*`.

## Further Docs

- [DEPLOYMENT.md](DEPLOYMENT.md) — deploy to a VPS
- [docs/RUNBOOK.md](docs/RUNBOOK.md) — operate in production
