# 🚀 Timetable LLM - Complete Startup Guide

## Quick Start (Recommended)

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16 (or Docker)
- Redis (or Docker)

### Option A: Docker Compose (Easiest)

```bash
cd c:\Timetable-LLM
docker compose up --build
```

**Access Points:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/api/docs
- Database: localhost:5432 (user: postgres, password: tiger)
- Redis: localhost:6379

---

## Option B: Local Development (Recommended for Development)

### 1. Set Up Backend

```bash
# Navigate to backend
cd c:\Timetable-LLM\backend

# Create virtual environment
python -m venv .venv

# Activate venv (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Set Up Frontend (in a NEW terminal)

```bash
# Navigate to frontend
cd c:\Timetable-LLM\frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

**Expected Output:**
```
  ▲ Next.js 15.3.9
  - Local:        http://localhost:3000
  - Environments: .env.local
```

---

## Configuration Checklist

### ✅ Environment Variables (.env)

The `.env` file has been configured with:

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:tiger@db:5432/timetable_db` | Docker Compose |
| `REDIS_URL` | `redis://redis:6379/0` | Docker Compose |
| `JWT_SECRET` | 64-char hex string | ✅ Already set |
| `LLM_PROVIDER` | `openai` | Change if using NVIDIA/Anthropic |
| `LLM_MODEL` | `gpt-3.5-turbo` | Change to your preferred model |
| `ENVIRONMENT` | `development` | ✅ Development mode enabled |
| `DEBUG` | `True` | ✅ Debug mode enabled |

### 📝 For Local PostgreSQL/Redis (Without Docker):

If you have PostgreSQL and Redis running locally, update `.env`:

```env
# Use individual components
DATABASE_URL=
DB_HOST=localhost
DB_PORT=5432
DB_NAME=timetable_db
DB_USER=postgres
DB_PASSWORD=tiger

# Redis local
REDIS_URL=redis://localhost:6379/0
```

---

## Testing Endpoints

### Backend Health

```bash
# Basic health
curl http://localhost:8000/health

# Live check
curl http://localhost:8000/health/live

# Readiness (checks DB + Redis)
curl http://localhost:8000/health/ready
```

### Frontend

Open http://localhost:3000 in your browser.

---

## Troubleshooting

### Backend Won't Start

#### Error: "DATABASE_URL must be configured"
- **Solution**: Ensure `.env` has a valid `DATABASE_URL` or `DB_*` variables set

#### Error: "ModuleNotFoundError: No module named 'app'"
- **Solution**: Ensure you're in the `backend` directory before running uvicorn

#### Error: "psycopg2 connection refused"
- **Solution**: 
  - If using Docker Compose: Ensure `db` service is running (`docker compose ps`)
  - If using local PostgreSQL: Ensure it's running on port 5432

#### Error: "alembic upgrade head" fails
- **Solution**: Check PostgreSQL is accessible and empty database exists

### Frontend Won't Start

#### Error: "Module not found: @/components/..."
- **Solution**: Run `npm install` again
- **Alternative**: Try `npm ci` (clean install) instead

#### Error: "NEXT_PUBLIC_API_URL undefined"
- **Solution**: Ensure `.env.local` exists in `frontend/` directory

#### Port 3000 already in use
- **Solution**: Kill the process or use: `npm run dev -- -p 3001`

### Database Issues

#### "table does not exist"
- **Solution**: Run `alembic upgrade head` in backend directory

#### "permission denied for database"
- **Solution**: Check `DB_USER` and `DB_PASSWORD` in `.env`

### Redis Connection Issues

#### "Error: connect ECONNREFUSED 127.0.0.1:6379"
- **Solution**: 
  - If using Docker: Ensure Redis container is running
  - If using local: Install and start Redis

---

## Next Steps

1. ✅ Start backend + frontend
2. ✅ Verify health endpoints
3. ✅ Open http://localhost:3000
4. 📝 Update `.env` with:
   - Real LLM API key (OpenAI/NVIDIA/Anthropic)
   - Firebase Project ID (if using Firebase auth)
   - SMTP credentials (if sending invites)
5. 🧪 Run tests: `cd backend && pytest -v`
6. 📊 Check API docs: http://localhost:8000/api/docs

---

## Useful Commands

```bash
# Backend
cd backend
pytest -v                              # Run tests
pytest --cov=app --cov-report=html    # Coverage report
alembic upgrade head                   # Apply migrations
alembic downgrade -1                   # Rollback one migration
alembic history                        # View migration history

# Frontend
cd frontend
npm run build                          # Build for production
npm run lint                           # Run ESLint
npm test                               # Run tests

# Docker
docker compose down                    # Stop all services
docker compose down -v                 # Stop + remove volumes
docker compose logs -f backend         # Follow backend logs
docker compose logs -f frontend        # Follow frontend logs
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  Frontend (Next.js)                             │
│  Port 3000 - React Components + Tailwind CSS    │
└──────────────────┬──────────────────────────────┘
                   │ HTTP/REST
┌──────────────────▼──────────────────────────────┐
│  Backend (FastAPI)                              │
│  Port 8000 - Python + LangChain + OR-Tools      │
├──────────────┬──────────────┬────────────────────┤
│              │              │                    │
│  LLM Calls   │  Constraint  │  Database Ops     │
│  (OpenAI/    │  Solver      │  (SQLAlchemy)     │
│  NVIDIA)     │  (OR-Tools)  │                    │
└──────────────┴──────────────┴────────┬───────────┘
                                       │
                        ┌──────────────┴──────────────┐
                        │                             │
            ┌───────────▼────────────┐    ┌──────────▼──────┐
            │  PostgreSQL 16         │    │  Redis 7        │
            │  Port 5432             │    │  Port 6379      │
            │  Multi-tenant data     │    │  Cache + Queue  │
            └────────────────────────┘    └─────────────────┘
```

---

## Support

For detailed documentation:
- API Reference: http://localhost:8000/api/docs (Swagger UI)
- Deployment: See [DEPLOYMENT.md](./DEPLOYMENT.md)
- Architecture: See [docs/](./docs/)
