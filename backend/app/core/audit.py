"""
Audit logging utility for tracking user actions.
"""
from sqlalchemy.orm import Session
from app.models.audit import AuditLog


def log_action(
    db: Session,
    institution_id: int,
    user_id: int | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
):
    """Record an audit log entry."""
    entry = AuditLog(
        institution_id=institution_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
