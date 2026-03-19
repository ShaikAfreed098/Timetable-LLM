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

# Create all database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="LLM-powered College Timetable Automation System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
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
