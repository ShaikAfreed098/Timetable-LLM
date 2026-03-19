# Timetable LLM

An **LLM-powered College Timetable Automation System** that replaces manual scheduling with an intelligent, constraint-aware AI system.

## Features

- 🤖 **AI Chat Interface** — Natural-language commands to manage faculty, subjects, rooms, and batches
- ⚙️ **Constraint Solver** — Google OR-Tools CP-SAT for conflict-free timetable generation
- 📅 **Timetable Grid** — Interactive display with per-batch views
- 📤 **Export** — Download timetables as PDF or Excel
- 🔒 **JWT Authentication** — Role-based access control (Super Admin, Department Admin, Faculty)
- 🐳 **Docker** — Full containerised deployment

## College Schedule (Pre-configured)

| Period | Time | Type |
|--------|------|------|
| P1 | 09:10–10:00 | Teaching |
| P2 | 10:00–10:50 | Teaching |
| Break | 10:50–11:00 | Short Break |
| P3 | 11:00–11:50 | Teaching |
| P4 | 11:50–12:40 | Teaching |
| Lunch | 12:40–13:30 | Lunch Break |
| P5 | 13:30–14:20 | Teaching |
| P6 | 14:20–15:10 | Teaching |
| P7 | 15:10–16:00 | Teaching |

## Quick Start

### With Docker Compose (Recommended)

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY and JWT_SECRET
docker compose up --build
```

Frontend: http://localhost:3000  
Backend API: http://localhost:8000  
API Docs: http://localhost:8000/api/docs

### Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env  # edit as needed
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Architecture

```
[ React/Next.js Chat UI ] → [ FastAPI Backend ]
                                    ├── LangChain LLM Agent (OpenAI)
                                    │     └── Tool calling → DB operations
                                    ├── OR-Tools Constraint Solver
                                    │     └── Conflict-free scheduling
                                    ├── PostgreSQL (data store)
                                    └── Export (PDF / Excel)
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/token` | Login (get JWT) |
| GET | `/api/faculty` | List faculty |
| POST | `/api/faculty` | Add faculty |
| GET | `/api/subjects` | List subjects |
| POST | `/api/subjects` | Add subject |
| GET | `/api/rooms` | List rooms |
| POST | `/api/rooms` | Add room |
| GET | `/api/batches` | List batches |
| POST | `/api/batches` | Add batch |
| POST | `/api/timetable/generate` | Generate timetable |
| GET | `/api/timetable/{id}` | Get timetable slots |
| GET | `/api/timetable/{id}/conflicts` | Check conflicts |
| POST | `/api/timetable/{id}/export` | Export PDF/Excel |
| POST | `/api/chat` | LLM chat (SSE stream) |

Full interactive docs at `/api/docs` (Swagger UI).

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (required for chat) |
| `DATABASE_URL` | SQLAlchemy DB URL (default: SQLite) |
| `REDIS_URL` | Redis connection string |
| `JWT_SECRET` | Secret for JWT signing |
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) |
| `LLM_MODEL` | LLM model name (default: `gpt-4o`) |

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 + TypeScript + Tailwind CSS |
| Backend | FastAPI + Python 3.11 |
| LLM | LangChain + OpenAI GPT-4o |
| Scheduler | Google OR-Tools CP-SAT |
| Database | PostgreSQL 15 / SQLite (dev) |
| Cache | Redis 7 |
| Export | ReportLab (PDF) + openpyxl (Excel) |
| Auth | JWT (python-jose + passlib/bcrypt) |
| Container | Docker + Docker Compose |
