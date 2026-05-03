"""
Celery tasks for heavy computation (timetable generation).
"""
import logging
from app.celery_app import celery_app
from app.database import SessionLocal
from app.core.scheduler import generate_timetable
from app.core.audit import log_action
from app.config import settings
import sentry_sdk

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=1.0 if settings.ENVIRONMENT != "production" else 0.1,
    )

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.generate_timetable_async")
def generate_timetable_async(self, semester: int, department: str, institution_id: int, user_id: int | None = None):
    """
    Async timetable generation task.
    Returns the result dict with timetable_id, slots_count, etc.
    """
    db = SessionLocal()
    try:
        self.update_state(state="PROGRESS", meta={"status": "Generating timetable..."})
        result = generate_timetable(db, semester, department, institution_id)

        # Audit log
        log_action(
            db=db,
            institution_id=institution_id,
            user_id=user_id,
            action="timetable.generate",
            entity_type="timetable",
            entity_id=result.get("timetable_id"),
            details={
                "semester": semester,
                "department": department,
                "slots_count": result.get("slots_count", 0),
                "conflicts": len(result.get("conflicts", [])),
            },
        )
        db.commit()

        return result
    except Exception as exc:
        logger.exception("Timetable generation failed")
        raise self.retry(exc=exc, max_retries=1, countdown=10)
    finally:
        db.close()


@celery_app.task(name="app.tasks.cleanup_audit_logs")
def cleanup_audit_logs():
    """
    Delete audit log entries older than AUDIT_LOG_RETENTION_DAYS.
    """
    from datetime import datetime, timedelta
    from app.config import settings
    from app.models.audit import AuditLog

    db = SessionLocal()
    try:
        threshold = datetime.utcnow() - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
        deleted = db.query(AuditLog).filter(AuditLog.created_at < threshold).delete()
        db.commit()
        logger.info(f"Cleaned up {deleted} audit log entries older than {threshold}")
        return {"deleted_count": deleted}
    except Exception:
        logger.exception("Audit log cleanup failed")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.send_email")
def send_email(to_email: str, subject: str, body: str):
    """
    Send an email using SMTP settings. Falls back to logging if SMTP_HOST is not set.
    """
    import smtplib
    from email.mime.text import MIMEText
    from app.config import settings

    if not settings.SMTP_HOST:
        logger.warning(f"SMTP_HOST not set. LOGGING EMAIL INSTEAD:\nTo: {to_email}\nSubject: {subject}\nBody: {body}")
        return {"status": "logged"}

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to_email

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.ENVIRONMENT != "development":
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email sent to {to_email}")
        return {"status": "sent"}
    except Exception:
        logger.exception(f"Failed to send email to {to_email}")
        raise
