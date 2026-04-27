# Deployment Guide — Timetable LLM SaaS

## Prerequisites

- Docker & Docker Compose (v2.x+)
- A `.env` file in the project root (see `.env.example`)
- A Firebase project for authentication
- An OpenAI / NVIDIA API key for the LLM

---

## Quick Start (Development)

```bash
# Clone the repo
git clone https://github.com/ShaikAfreed098/Timetable-LLM.git
cd Timetable-LLM

# Copy and edit environment variables
cp .env.example .env
# Edit .env with your values

# Start services
docker-compose up --build
```

- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/api/docs

---

## Production Deployment

### 1. Environment Variables

Create a `.env` file with production values:

```env
# Database
POSTGRES_USER=timetable
POSTGRES_PASSWORD=<strong-random-password>
POSTGRES_DB=timetable_db
DATABASE_URL=postgresql://timetable:<password>@db:5432/timetable_db

# JWT
JWT_SECRET_KEY=<generate-with: openssl rand -hex 32>
JWT_EXPIRE_MINUTES=60

# LLM
OPENAI_API_KEY=<your-api-key>
LLM_MODEL=gpt-4o

# Firebase
FIREBASE_SERVICE_ACCOUNT_KEY=<path-or-json>

# App
ALLOWED_ORIGINS=https://yourdomain.com
DEBUG=false

# Redis (for Celery)
REDIS_URL=redis://redis:6379/0
```

### 2. Deploy with Docker Compose

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

This starts:
- **PostgreSQL 16** with persistent data
- **Redis 7** for Celery message broker
- **Backend** (FastAPI + Uvicorn) with auto-migration
- **Celery Worker** for async timetable generation
- **Frontend** (Next.js)

### 3. Database Migrations

Migrations run automatically on backend startup via `alembic upgrade head`. For manual migrations:

```bash
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 4. Verify Deployment

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status": "ok"}

# API docs
open http://localhost:8000/api/docs
```

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend   │────▶│   Backend    │────▶│  PostgreSQL  │
│  (Next.js)   │     │  (FastAPI)   │     │     16       │
│  port 3000   │     │  port 8000   │     │  port 5432   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐     ┌─────────────┐
                    │   Celery      │────▶│    Redis      │
                    │   Worker      │     │   port 6379   │
                    └──────────────┘     └─────────────┘
```

### Multi-Tenancy

- Each institution gets isolated data via `institution_id` foreign keys
- Users are scoped to institutions via the invite system
- Schedule configuration is per-institution

### Security

- **Authentication**: Firebase Auth (Google Sign-In) + JWT fallback
- **Authorization**: Role-based (super_admin, admin, department_admin, faculty)
- **Rate Limiting**: 200 requests/minute per IP (configurable)
- **Security Headers**: X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
- **Audit Logging**: All significant actions are logged with user/IP/timestamp

---

## CI/CD

The project includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that:

1. **Backend Tests**: Runs pytest against a Postgres service container
2. **Frontend Build**: Verifies the Next.js app builds without errors
3. **Docker Build**: Builds both images on `main` branch pushes

---

## Scaling

- **Celery Workers**: Scale with `docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=4`
- **Backend**: Run multiple instances behind a load balancer
- **Database**: Use managed PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
- **Redis**: Use managed Redis (ElastiCache, Memorystore, etc.)
