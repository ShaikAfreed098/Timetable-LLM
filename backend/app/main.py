import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.config import settings
from app.database import engine
import app.models  # register all models
import sentry_sdk

from app.api.auth import router as auth_router
from app.api.invites import router as invites_router
from app.api.faculty import router as faculty_router
from app.api.subject import router as subject_router
from app.api.room import router as room_router
from app.api.batch import router as batch_router
from app.api.timetable import router as timetable_router
from app.api.chat import router as chat_router
from app.api.config import router as config_router
from app.api.institution import router as institution_router
from app.api.audit import router as audit_router

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=1.0 if settings.ENVIRONMENT != "production" else 0.1,
        profiles_sample_rate=1.0 if settings.ENVIRONMENT != "production" else 0.1,
    )

logger = logging.getLogger("timetable")

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE * 10}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    errors = settings.validate_for_production()
    if errors:
        for e in errors:
            logger.error("CONFIG ERROR: %s", e)
        if settings.ENVIRONMENT == "production":
            sys.exit("Refusing to start: invalid production configuration.")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="LLM-powered College Timetable Automation SaaS",
    version="2.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'"
        )
    return response


app.include_router(auth_router)
app.include_router(invites_router)
app.include_router(faculty_router)
app.include_router(subject_router)
app.include_router(room_router)
app.include_router(batch_router)
app.include_router(timetable_router)
app.include_router(chat_router)
app.include_router(config_router)
app.include_router(institution_router)
app.include_router(audit_router)


@app.get("/")
def root():
    return {"message": "Timetable LLM SaaS API is running.", "docs": "/api/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/live")
def health_live():
    return {"status": "live"}


@app.get("/health/ready")
def health_ready():
    checks = {"db": False, "redis": False}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["db"] = True
    except Exception as e:
        logger.warning("DB health check failed: %s", e)
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        r.ping()
        checks["redis"] = True
    except Exception as e:
        logger.warning("Redis health check failed: %s", e)
    ok = all(checks.values())
    return Response(
        content='{"status":"' + ("ready" if ok else "degraded") + '","checks":' +
                '{"db":' + str(checks["db"]).lower() + ',"redis":' + str(checks["redis"]).lower() + '}}',
        media_type="application/json",
        status_code=200 if ok else 503,
    )
