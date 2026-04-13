# 📚 Timetable-LLM — Complete Project Explanation (Beginner to Expert)

> This document explains **every single part** of this project — what it does, why it exists, and how it works together. Written for someone who is learning programming and wants to understand the real world.

---

## 🌍 WHAT IS THIS PROJECT?

This is a **college timetable automation system**. Normally, a college administrator manually arranges a schedule — which teacher takes which class, in which room, on which day and period. This is very complex and error-prone.

This project **automates** that process using two powerful technologies:
1. **AI/LLM (Large Language Model)** — You talk to it in plain English ("Add Professor Smith to the CS department"), and it performs the action.
2. **Constraint Solver (OR-Tools)** — A mathematical engine that generates a conflict-free timetable automatically, ensuring no teacher is in two places at once, no room is double-booked, etc.

---

## 🗂️ PROJECT FOLDER STRUCTURE (Every file explained)

```
Timetable-LLM/
├── .env                        ← Secret configuration (passwords, API keys)
├── .gitignore                  ← Tells Git which files NOT to upload (like .env)
├── docker-compose.yml          ← One command to run the whole application
├── README.md                   ← Basic project overview
├── PROJECT_EXPLAINED.md        ← THIS FILE (full explanation)
│
├── backend/                    ← The SERVER (Python / FastAPI)
│   ├── Dockerfile              ← Instructions to package backend for Docker
│   ├── entrypoint.sh           ← Script that runs when Docker container starts
│   ├── requirements.txt        ← All Python packages this project needs
│   ├── alembic.ini             ← Configuration for Alembic (database migration tool)
│   ├── seed_data.py            ← Script to add sample data to the database
│   ├── create_admin.py         ← Script to create the first admin user
│   │
│   ├── alembic/                ← Database migration folder
│   │   ├── env.py              ← Tells Alembic how to connect to the DB
│   │   └── versions/           ← Each file here = one database schema change
│   │       └── a8e84e3e134e_init.py  ← First migration: creates all tables
│   │
│   └── app/                    ← Main application code
│       ├── main.py             ← Entry point of the app (starts everything)
│       ├── config.py           ← Reads settings from .env file
│       ├── database.py         ← Database connection setup
│       │
│       ├── models/             ← Database table definitions
│       │   ├── faculty.py      ← Faculty/Teacher table
│       │   ├── subject.py      ← Subject table
│       │   ├── room.py         ← Room table
│       │   ├── batch.py        ← Student Batch/Section table
│       │   ├── timetable.py    ← Assignment & TimetableSlot tables
│       │   ├── user.py         ← User (login accounts) table
│       │   └── constraint.py   ← Scheduling constraints table
│       │
│       ├── api/                ← HTTP API routes (what the frontend calls)
│       │   ├── auth.py         ← Login / Register endpoints
│       │   ├── faculty.py      ← Add/List/Delete faculty
│       │   ├── subject.py      ← Add/List/Delete subjects
│       │   ├── room.py         ← Add/List/Delete rooms
│       │   ├── batch.py        ← Add/List/Delete batches
│       │   ├── timetable.py    ← Generate timetable, view, export
│       │   └── chat.py         ← AI chat endpoint
│       │
│       ├── core/               ← Business logic (the smart stuff)
│       │   ├── auth.py         ← Password hashing, JWT token logic
│       │   ├── scheduler.py    ← OR-Tools constraint solver
│       │   ├── llm_agent.py    ← AI/LLM brain (LangChain + OpenAI/NVIDIA)
│       │   └── export.py       ← PDF and Excel generation
│       │
│       └── schemas/            ← Data validation shapes (Pydantic)
│
└── frontend/                   ← The USER INTERFACE (Next.js / React)
    ├── Dockerfile              ← Instructions to package frontend for Docker
    ├── next.config.js          ← Next.js configuration
    ├── package.json            ← All JavaScript packages this project needs
    └── src/
        ├── app/                ← Next.js pages (each file = one URL page)
        ├── components/         ← Reusable UI pieces (buttons, tables, etc.)
        ├── lib/                ← Helper functions (API calls, utilities)
        └── store/              ← Global state management (Zustand)
```

---

## 🏗️ HOW IT ALL WORKS TOGETHER (The Big Picture)

```
[User's Browser]
      │
      │  HTTP requests (JSON)
      ▼
[Next.js Frontend :3000]  ──────────────────────────────────────────────┐
      │                                                                   │
      │  API calls to backend                                             │
      ▼                                                                   │
[FastAPI Backend :8000]                                                   │
      │                                                                   │
      ├──► [LLM Agent] ──► AI understands plain English → calls tools    │
      │                                                                   │
      ├──► [Scheduler] ──► OR-Tools solves the constraint problem        │
      │                                                                   │
      ├──► [MySQL Database] ──► Stores all data permanently              │
      │                                                                   │
      └──► [Redis] ──► Fast temporary storage (sessions, caching)        │
                                                                         │
[NVIDIA / OpenAI API] ◄──────────────────────────────────────────────────┘
      (LLM responses come from here)
```

**Think of it like a restaurant:**
- **Frontend** = The menu and dining room (what the customer sees)
- **Backend API** = The kitchen (processes orders)
- **Database** = The pantry (stores ingredients/data)
- **LLM Agent** = The head chef who understands special requests
- **Scheduler** = The kitchen manager who arranges who cooks what
- **Redis** = The prep station (fast temporary storage)

---

## 🔧 THE BACKEND — Deep Dive

### 1. `app/main.py` — The Application Entry Point

This is the **first file** that runs. Think of it as the front door of the building.

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)   # Create all DB tables
    _ensure_super_admin(SessionLocal)        # Create default admin user
    yield                                    # App runs here
```

**What happens at startup:**
1. All database tables are created (if they don't exist)
2. A default Super Admin user is created (if none exists)
3. All API routes are registered
4. The CORS middleware is enabled (allows the frontend to talk to backend)

**CORS** = Cross-Origin Resource Sharing. Without this, your browser would block the frontend (`localhost:3000`) from talking to the backend (`localhost:8000`) because they are on different "ports".

---

### 2. `app/config.py` — The Settings Manager

This file reads your `.env` file and makes all settings available everywhere.

```python
class Settings(BaseSettings):
    OPENAI_API_KEY: Optional[str] = None    # Your AI API key
    DATABASE_URL: Optional[str] = None       # Where to find the database
    JWT_SECRET: str = "change-me"            # Used to sign login tokens
    ALLOWED_ORIGINS: str = "http://localhost:3000"
```

**Why Pydantic Settings?** It automatically validates types. If you put `"abc"` for an integer field, it raises an error immediately — instead of silently breaking later.

**The `get_database_url()` method** is smart — it supports three formats:
- A full `DATABASE_URL` string → uses it directly
- Individual `DB_HOST`, `DB_USER`, `DB_NAME` etc. → builds the URL safely (handles special characters in passwords)
- Nothing set → falls back to SQLite (a local file database for testing)

---

### 3. `app/database.py` — The Database Connection

```python
engine = create_engine(DATABASE_URL)           # Connection pool to MySQL
SessionLocal = sessionmaker(bind=engine)       # Factory for DB sessions

def get_db():
    db = SessionLocal()
    try:
        yield db        # Give the DB session to the API handler
    finally:
        db.close()      # Always close when done!
```

**What is a Session?** Think of it like opening a notebook to write something. You open it (`SessionLocal()`), make notes (queries/writes), and close it when done. The `get_db()` function is used as a **FastAPI Dependency** — any API route that needs the database just declares `db: Session = Depends(get_db)` and FastAPI automatically provides it.

---

### 4. `app/models/` — The Database Tables

Each Python class here = one table in the MySQL database.

#### `faculty.py` — Teacher records
```
id | name | department | email | max_periods_per_day | unavailable_slots | is_active
```
- `unavailable_slots` is stored as **JSON** — e.g.: `[{"day": "Monday", "period": 1}]`
- This means the teacher cannot be scheduled on that slot

#### `subject.py` — Subject records
```
id | name | code | department | credits | periods_per_week | requires_lab
```
- `requires_lab = True` means this subject needs a lab room, not a classroom

#### `room.py` — Room records
```
id | room_number | capacity | type | floor | building
```
- `type` is an enum: `classroom` or `lab`
- The scheduler uses this to match lab subjects to lab rooms

#### `batch.py` — Student group records
```
id | name | department | semester | student_count | year
```
- A "batch" is a group of students. E.g., "CS-A Semester 3" is one batch.

#### `timetable.py` — The generated schedule
Two tables:
- **Assignment**: Links a Faculty → Subject → Batch (teaches this subject to this batch)
- **TimetableSlot**: Each row is one cell in the final timetable grid (day + period + batch + teacher + room + subject)

#### `user.py` — Login accounts
```
id | username | email | hashed_password | role | is_active
```
- `role` can be: `super_admin`, `department_admin`, or `faculty`
- Passwords are **never stored in plain text** — always bcrypt-hashed

---

### 5. `app/api/` — The REST API Endpoints

These are the URLs that the frontend calls. Every file here is a **router** (a group of related endpoints).

#### `auth.py` — Login System
| Method | URL | What it does |
|--------|-----|-------------|
| POST | `/api/auth/token` | Login with username+password → returns a JWT token |
| POST | `/api/auth/register` | Create a new user account |
| GET | `/api/auth/me` | Get the currently logged-in user's info |

**How JWT works:**
1. User logs in → Backend checks password → Returns a token (like a key card)
2. Every future request includes this token in the header
3. Backend verifies the token → knows who the user is without checking the database again

#### `faculty.py`, `subject.py`, `room.py`, `batch.py` — CRUD APIs
All follow the same pattern:
- `GET /api/faculty` → List all faculty
- `POST /api/faculty` → Add a new faculty
- `GET /api/faculty/{id}` → Get one faculty
- `PUT /api/faculty/{id}` → Update faculty
- `DELETE /api/faculty/{id}` → Delete faculty

All protected — you must be logged in (valid JWT token required).

#### `timetable.py` — The Core Timetable API
| Method | URL | What it does |
|--------|-----|-------------|
| POST | `/api/timetable/assignments` | Create a faculty-subject-batch assignment |
| GET | `/api/timetable/assignments` | List all assignments |
| POST | `/api/timetable/generate` | **Trigger the OR-Tools solver** |
| GET | `/api/timetable/{id}` | Get all slots for a timetable |
| PUT | `/api/timetable/{id}/slot` | Manually edit one slot |
| GET | `/api/timetable/{id}/conflicts` | Check for conflicts |
| POST | `/api/timetable/{id}/export` | Download as PDF or Excel |

#### `chat.py` — The AI Chat API
| Method | URL | What it does |
|--------|-----|-------------|
| POST | `/api/chat` | Send a message → AI processes it and responds |

This uses **Server-Sent Events (SSE)** — the response streams back word-by-word (like ChatGPT typing effect).

---

### 6. `app/core/auth.py` — Password & Token Logic

```python
pwd_context = CryptContext(schemes=["bcrypt"])    # bcrypt hashing

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)             # "hello" → "$2b$12$abc..."

def verify_password(plain, hashed) -> bool:
    return pwd_context.verify(plain, hashed)      # Compare safely
```

**Why bcrypt?** You cannot reverse a bcrypt hash to get the original password. Even if hackers steal your database, they cannot read the passwords.

---

### 7. `app/core/scheduler.py` — The Constraint Solver (The Smartest Part)

This is where the magic happens. It uses **Google OR-Tools CP-SAT solver** — a mathematical engine used by Google to solve real-world scheduling problems.

**The Problem it Solves:**
- We have N batches, M teachers, K rooms, and 42 time slots (6 days × 7 periods)
- Each teacher-subject-batch assignment must be placed exactly once
- No teacher can be in two places at the same time
- No room can be used for two batches simultaneously
- Teachers have unavailable time slots (blocked)
- Labs must use lab rooms; regular classes use classrooms

**How it solves (step by step):**

```
Step 1: Load data from database (batches, teachers, subjects, rooms, assignments)

Step 2: Create decision variables
  - cell[batch, day, period] = which assignment (or "free") fills this slot

Step 3: Add constraints
  - Every assignment must be placed exactly once
  - No faculty double-booking
  - No room double-booking
  - Faculty unavailable slots are blocked

Step 4: Set objective (minimize "same subject twice on same day")

Step 5: Solve! (max 30 seconds)

Step 6: Extract solution → save TimetableSlot records to database
```

**College Schedule Config:**
```python
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
TEACHING_PERIODS = [1, 2, 3, 4, 5, 6, 7]  # 7 periods per day

PERIOD_TIMES = {
    1: "09:10–10:00",
    2: "10:00–10:50",
    3: "11:00–11:50",   # After 10-min break
    4: "11:50–12:40",
    5: "13:30–14:20",   # After 50-min lunch
    6: "14:20–15:10",
    7: "15:10–16:00",
}
```

---

### 8. `app/core/llm_agent.py` — The AI Brain

This is the AI chat system. It uses **LangChain** to connect to an LLM (either OpenAI GPT or NVIDIA's NIM API).

**How it works:**
1. User sends a message: _"Add a subject called Data Structures with code CS201, 3 credits, no lab required"_
2. The LLM reads the message and decides to call the `add_subject` tool
3. The tool executes the database insert
4. LLM responds: _"I've added Data Structures (CS201) successfully!"_

**Available Tools** (things the AI can do):
- `add_faculty` → Inserts a faculty record
- `add_subject` → Inserts a subject record
- `add_room` → Inserts a room record
- `add_batch` → Inserts a batch record
- `assign_subject` → Creates faculty-subject-batch assignment
- `generate_timetable` → Triggers the OR-Tools solver
- `check_conflicts` → Runs conflict checker
- `get_faculty_schedule` → Queries a teacher's schedule

**NVIDIA Support:** If the API key starts with `nvapi-`, the code automatically sets the base URL to NVIDIA's NIM endpoint and uses a compatible open-source model.

---

### 9. `alembic/` — Database Migrations

**What is Alembic?** It's a version control system for your database schema. Like Git for your database.

**Why needed?** When you add a new column to a table, you can't just change the Python model — the actual MySQL table needs to be altered too. Alembic generates SQL migration scripts to do this safely.

```bash
alembic revision --autogenerate -m "Add column X"  # Detect model changes
alembic upgrade head                                 # Apply changes to DB
alembic downgrade -1                                 # Undo last change
```

**`alembic/env.py`** — Modified to read `DATABASE_URL` from app settings instead of hardcoding it, so it always uses the right database.

---

## 🎨 THE FRONTEND — Deep Dive

Built with **Next.js 15** (React framework) + **TypeScript** + **Tailwind CSS**.

### How Next.js Routing Works
Every file inside `src/app/` becomes a page:
- `src/app/page.tsx` → `http://localhost:3000/` (Home/Login page)
- `src/app/dashboard/page.tsx` → `http://localhost:3000/dashboard`
- `src/app/timetable/page.tsx` → `http://localhost:3000/timetable`

### `src/lib/` — API Helpers
Contains functions that make HTTP requests to the backend:
```typescript
// Example: calling the backend login API
const response = await fetch('http://localhost:8000/api/auth/token', {
  method: 'POST',
  body: JSON.stringify({ username, password })
})
```

### `src/store/` — Global State (Zustand)
Zustand is a simple state manager. It stores things like:
- Is the user logged in?
- What is the current timetable ID?
- What error messages to show?

This allows any component anywhere in the app to access and update shared data.

### `src/components/` — Reusable UI Parts
Examples:
- `ChatPanel` — the AI chat interface
- `TimetableGrid` — the schedule displayed as a grid
- `FacultyTable` — list of teachers
- `Sidebar` — navigation menu

### `next.config.js` — Important Setting
```javascript
const nextConfig = {
  output: "standalone",  // Makes the build work inside Docker!
}
```
The `standalone` output bundles everything needed into one folder, which the Docker container can run with just `node server.js`.

---

## 🐳 DOCKER — How Deployment Works

Docker packages each service into an isolated container, so it runs identically on any machine.

### `docker-compose.yml` — Orchestrates All Services

```yaml
services:
  backend:  ← FastAPI Python server (port 8000)
  frontend: ← Next.js React app (port 3000)
  db:       ← MySQL 8.0 database (port 3306)
  redis:    ← Redis cache (port 6379)
```

**When you run `docker compose up --build`, this happens:**
1. Docker builds the backend image (installs Python packages)
2. Docker builds the frontend image (installs npm packages, builds Next.js)
3. MySQL container starts and waits to be healthy
4. Redis container starts
5. Backend container starts → runs `entrypoint.sh`:
   - `alembic upgrade head` → applies database migrations
   - `uvicorn app.main:app` → starts the API server
   - On startup, creates tables and seeds the Super Admin user
6. Frontend container starts → serves the web app

### `backend/Dockerfile` — How the Python server is packaged:
```dockerfile
FROM python:3.11-slim          # Start from a slim Python image
RUN apt-get install gcc ...    # Install system dependencies for MySQL
COPY requirements.txt .        # Copy package list
RUN pip install -r requirements.txt  # Install all packages
COPY . .                       # Copy the app code
CMD ["sh", "entrypoint.sh"]    # Run the startup script
```

### `frontend/Dockerfile` — How the Next.js app is packaged:
Multi-stage build for efficiency:
1. **deps stage** — Install npm packages
2. **builder stage** — Build the production Next.js bundle
3. **runner stage** — Run only the built output (smaller final image)

---

## 🔐 SECURITY

### Authentication Flow
```
User → POST /api/auth/token (username + password)
     → Backend verifies password with bcrypt
     → Returns JWT token (valid for 24 hours)
     → Future requests: Authorization: Bearer <token>
     → Backend decodes token → gets user identity
```

### Role-Based Access Control
| Role | What they can do |
|------|-----------------|
| `super_admin` | Everything — manage all departments |
| `department_admin` | Manage their own department only |
| `faculty` | View only — see their own schedule |

### `.env` File
Contains all secrets. **Never committed to Git** (it's in `.gitignore`).
```
OPENAI_API_KEY=your-api-key       ← AI API key
JWT_SECRET=random-long-string      ← Signs login tokens (keep secret!)
DB_PASSWORD=yourdbpassword         ← Database password
```

---

## 🗃️ DATABASE SCHEMA DIAGRAM

```
users
  id, username, email, hashed_password, role, is_active

faculty ───────────────────────────────────────────────────┐
  id, name, department, email, max_periods_per_day,        │
  unavailable_slots (JSON), is_active                      │
                                                           │
subjects ──────────────────────────────────────────────┐   │
  id, name, code, department, credits,                 │   │
  periods_per_week, requires_lab                       │   │
                                                       │   │
batches ────────────────────────────────────────────┐  │   │
  id, name, department, semester, student_count, year│  │   │
                                                     │  │   │
rooms                                                │  │   │
  id, room_number, capacity, type, floor, building   │  │   │
                                                     │  │   │
assignments ─────────────────────────────────────────┼──┼───┤
  id, faculty_id (FK→faculty), subject_id (FK→subj), │  │   │
  batch_id (FK→batches), semester                    │  │   │
                                                     │  │   │
timetable_slots ─────────────────────────────────────┘──┘───┘
  id, timetable_id (UUID), batch_id (FK→batches),
  day_of_week, period_number, subject_id (FK),
  faculty_id (FK), room_id (FK), slot_type
```

---

## 💾 THE SEED DATA (What Was Pre-loaded)

When you ran `seed_data.py`, these were inserted:

**10 Faculty Members:**
Prof. Smith (CS), Prof. Lee (CS), Prof. Kumar (Mechanical), Prof. Sharma (Electrical), Prof. Rao (Civil), Prof. Iyer (CS), Prof. Nair (Mechanical), Prof. Gupta (Electrical), Prof. Banerjee (CS), Prof. Fernandes (Civil)

**15 Subjects:** Data Structures, Algorithms, OS, Networks, SE, Database Lab, Thermodynamics, Fluid Mechanics, Electrical Circuits, Control Systems, Strength of Materials, Survey Lab, Computer Lab, Machine Design, Structural Analysis

**10 Rooms:** 4 labs (L101, L201, L301, L401) + 6 classrooms (C101–C106)

**6 Batches:** CS-A Sem3, CS-B Sem3, ME-A Sem5, EE-A Sem3, CE-A Sem5, CE-B Sem5

**15 Assignments:** Each batch–faculty–subject mapping needed to generate the timetable.

---

## 🚀 HOW TO RUN THE PROJECT

### Option A — Local Development (Without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
alembic upgrade head           # Create database tables
python seed_data.py            # Load sample data
uvicorn app.main:app --reload  # Start server at :8000
```

**Frontend:**
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev                    # Start at :3000
```

### Option B — Docker (Recommended for deployment)
```bash
# Make sure .env is filled with your real values
docker compose up --build
```
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs

### Login Credentials (Default)
```
Username: admin
Password: admin123
```
⚠️ **Change this password immediately after first login!**

---

## 🔄 DATA FLOW — How a Timetable Gets Generated

```
1. Admin logs in → Gets JWT token

2. Admin uses Chat UI or API to ensure:
   - Faculties are loaded ✓
   - Subjects are loaded ✓
   - Rooms are loaded ✓
   - Batches are loaded ✓
   - Assignments (who teaches what) are loaded ✓

3. Admin calls: POST /api/timetable/generate?semester=3&department=CS

4. Backend (scheduler.py):
   a. Fetches all CS Semester 3 batches from DB
   b. Fetches all assignments for those batches
   c. Fetches faculty, rooms, subjects
   d. Builds CP-SAT model with constraints
   e. Runs solver (up to 30 seconds)
   f. Extracts solution → saves TimetableSlot records
   g. Returns timetable_id (UUID)

5. Frontend fetches: GET /api/timetable/{timetable_id}
   → Displays the grid

6. Admin can:
   - Export to PDF: POST /api/timetable/{id}/export?format=pdf
   - Export to Excel: POST /api/timetable/{id}/export?format=excel
   - Check for conflicts: GET /api/timetable/{id}/conflicts
   - Edit a slot manually: PUT /api/timetable/{id}/slot
```

---

## 🤖 HOW THE AI CHAT WORKS (Step by Step)

```
User types: "Generate a timetable for CS department, semester 3"

1. Message goes to: POST /api/chat

2. chat.py calls llm_agent.py → passes message to LLM

3. LLM (meta/llama-3.1-70b via NVIDIA API) reads the message
   and sees it should call the "generate_timetable" tool

4. Tool call: generate_timetable(semester=3, department="CS")
   → Internally calls scheduler.py
   → Returns timetable_id

5. LLM formats a nice response:
   "I've generated the timetable! Timetable ID: abc-123.
    Here's a summary: CS-A has 3 subjects scheduled on Monday..."

6. Response streams back to user via SSE (word by word)
```

---

## 📦 KEY PYTHON PACKAGES (requirements.txt explained)

| Package | Purpose |
|---------|---------|
| `fastapi` | The web framework — handles HTTP requests |
| `uvicorn` | The web server that runs FastAPI |
| `sqlalchemy` | Database ORM — Python ↔ MySQL |
| `alembic` | Database migrations |
| `pymysql` | MySQL driver for SQLAlchemy |
| `pydantic` | Data validation |
| `pydantic-settings` | Read settings from .env |
| `python-jose` | Create and verify JWT tokens |
| `passlib[bcrypt]` | Hash passwords securely |
| `bcrypt==3.2.2` | Pinned version to fix passlib compatibility |
| `langchain` | Framework to build AI agents |
| `langchain-openai` | LangChain's OpenAI/NVIDIA integration |
| `ortools` | Google's constraint solver |
| `reportlab` | Generate PDF files |
| `openpyxl` | Generate Excel files |

---

## 📦 KEY NPM PACKAGES (package.json explained)

| Package | Purpose |
|---------|---------|
| `next` | React framework with routing, SSR |
| `react` | UI component library |
| `typescript` | Type safety for JavaScript |
| `tailwindcss` | Utility-first CSS styling |
| `lucide-react` | Icon library |
| `zustand` | Simple global state management |

---

## ⚠️ KNOWN LIMITATIONS & FUTURE IMPROVEMENTS

1. **Admin password** — Default `admin123` should be changed after setup
2. **No email verification** — Users are created without email confirmation
3. **Single database** — For very large colleges, consider database sharding
4. **LLM cost** — Every chat message calls the AI API (costs money per request)
5. **Solver time limit** — Very complex schedules (many batches) may hit 30-second timeout
6. **No real-time updates** — If two admins edit simultaneously, conflicts can occur

---

## 🎓 SUMMARY — One Paragraph

This project is a full-stack web application that automates college timetable generation. The **frontend** (Next.js) provides a modern web interface with an AI chat panel. The **backend** (FastAPI + Python) handles all business logic — it exposes REST APIs used by the frontend, runs an AI agent (LLM via LangChain + NVIDIA) that understands plain English commands, and uses Google's OR-Tools to solve the scheduling constraint problem mathematically. All data is stored in a **MySQL database** managed by SQLAlchemy and Alembic. The entire system is Dockerized — a single `docker compose up --build` starts MySQL, Redis, the backend, and the frontend together, automatically running all database migrations and seeding the first admin user.

---

*Generated for Timetable-LLM | March 2026*
