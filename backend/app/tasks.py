"""
Celery tasks for heavy computation (timetable generation).
"""
import logging
from app.celery_app import celery_app
from app.database import SessionLocal
from app.core.scheduler import generate_timetable
from app.core.audit import log_action

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

        return result
    except Exception as exc:
        logger.exception("Timetable generation failed")
        raise self.retry(exc=exc, max_retries=1, countdown=10)
    finally:
        db.close()
