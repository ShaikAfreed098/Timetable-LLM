from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
import app.models  # ensure all models are registered

from app.api.auth import router as auth_router
from app.api.faculty import router as faculty_router
from app.api.subject import router as subject_router
from app.api.room import router as room_router
from app.api.batch import router as batch_router
from app.api.timetable import router as timetable_router
from app.api.chat import router as chat_router

from contextlib import asynccontextmanager

def _ensure_super_admin(db_session):
    """Create a default super_admin user if none exists."""
    from app.models.user import User
    from app.core.auth import get_password_hash
    from sqlalchemy.orm import Session
    with db_session() as db:
        existing = db.query(User).filter(User.role == "super_admin").first()
        if not existing:
            hashed_pw = get_password_hash("admin123")
            admin = User(
                username="admin",
                email="admin@college.edu",
                hashed_password=hashed_pw,
                role="super_admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all database tables
    Base.metadata.create_all(bind=engine)
    # Seed Super Admin if not present (non-fatal — may fail locally if bcrypt version mismatches)
    try:
        from app.database import SessionLocal
        _ensure_super_admin(SessionLocal)
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning("Super-admin seed skipped: %s", exc)
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="LLM-powered College Timetable Automation System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth_router)
app.include_router(faculty_router)
app.include_router(subject_router)
app.include_router(room_router)
app.include_router(batch_router)
app.include_router(timetable_router)
app.include_router(chat_router)


@app.get("/")
def root():
    return {"message": "Timetable LLM API is running.", "docs": "/api/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
