from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.auth import require_role
from app.models.audit import AuditLog
from app.models.user import User

router = APIRouter(prefix="/api/audit", tags=["audit"])

@router.get("")
def list_audit_logs(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    q = (
        db.query(AuditLog)
        .filter(AuditLog.institution_id == current_user.institution_id)
        .order_by(AuditLog.created_at.desc())
    )
    total = q.count()
    rows = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "user_id": r.user_id,
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "details": r.details,
                "ip_address": r.ip_address,
            }
            for r in rows
        ],
    }
