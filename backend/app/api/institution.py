"""
Institution-level endpoints for data portability and erasure.

Supports GDPR Art. 20 (data portability) and Art. 17 (right to erasure),
and the equivalent rights under India's DPDP Act.
"""
from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime
from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.institution import Institution
from app.models.faculty import Faculty
from app.models.subject import Subject
from app.models.room import Room
from app.models.batch import Batch
from app.models.timetable import Assignment, TimetableSlot
from app.models.invite import Invite
from app.models.config import ScheduleConfig
from app.models.audit import AuditLog
from app.core.auth import require_role
from app.core.audit import log_action

router = APIRouter(prefix="/api/institution", tags=["institution"])


def _csv_bytes(rows: Iterable[dict], fieldnames: list[str]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in fieldnames})
    return buf.getvalue().encode("utf-8")


def _dump(query_result, fields: list[str]) -> list[dict]:
    return [{f: getattr(obj, f, None) for f in fields} for obj in query_result]


@router.get("/export")
def export_institution(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """Return a ZIP containing CSVs of all data scoped to the caller's institution."""
    iid = current_user.institution_id
    inst = db.query(Institution).filter(Institution.id == iid).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    tables: dict[str, tuple[list[dict], list[str]]] = {
        "institution.csv": (
            _dump([inst], ["id", "name", "slug", "grouping_scheme", "is_active"]),
            ["id", "name", "slug", "grouping_scheme", "is_active"],
        ),
        "users.csv": (
            _dump(
                db.query(User).filter(User.institution_id == iid).all(),
                ["id", "username", "email", "role", "department", "is_active"],
            ),
            ["id", "username", "email", "role", "department", "is_active"],
        ),
        "faculty.csv": (
            _dump(
                db.query(Faculty).filter(Faculty.institution_id == iid).all(),
                ["id", "name", "department", "email", "max_periods_per_day", "is_active"],
            ),
            ["id", "name", "department", "email", "max_periods_per_day", "is_active"],
        ),
        "subjects.csv": (
            _dump(
                db.query(Subject).filter(Subject.institution_id == iid).all(),
                ["id", "name", "code", "department", "credits", "periods_per_week", "requires_lab"],
            ),
            ["id", "name", "code", "department", "credits", "periods_per_week", "requires_lab"],
        ),
        "rooms.csv": (
            _dump(
                db.query(Room).filter(Room.institution_id == iid).all(),
                ["id", "room_number", "capacity", "type", "floor", "building"],
            ),
            ["id", "room_number", "capacity", "type", "floor", "building"],
        ),
        "batches.csv": (
            _dump(
                db.query(Batch).filter(Batch.institution_id == iid).all(),
                ["id", "name", "department", "semester", "student_count", "year"],
            ),
            ["id", "name", "department", "semester", "student_count", "year"],
        ),
        "assignments.csv": (
            _dump(
                db.query(Assignment).filter(Assignment.institution_id == iid).all(),
                ["id", "faculty_id", "subject_id", "batch_id", "semester"],
            ),
            ["id", "faculty_id", "subject_id", "batch_id", "semester"],
        ),
        "timetable_slots.csv": (
            _dump(
                db.query(TimetableSlot).filter(TimetableSlot.institution_id == iid).all(),
                [
                    "id", "timetable_id", "batch_id", "day_of_week",
                    "period_number", "subject_id", "faculty_id", "room_id", "slot_type",
                ],
            ),
            [
                "id", "timetable_id", "batch_id", "day_of_week",
                "period_number", "subject_id", "faculty_id", "room_id", "slot_type",
            ],
        ),
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for filename, (rows, fields) in tables.items():
            z.writestr(filename, _csv_bytes(rows, fields))
        z.writestr("README.txt", (
            f"Timetable-LLM data export\n"
            f"Institution: {inst.name} (id={inst.id}, slug={inst.slug})\n"
            f"Exported at: {datetime.utcnow().isoformat()}Z\n"
            f"Exported by: {current_user.email}\n"
        ).encode("utf-8"))

    log_action(
        db=db,
        institution_id=iid,
        user_id=current_user.id,
        action="institution.export",
        entity_type="institution",
        entity_id=str(iid),
        details={"exporter": current_user.email},
    )
    db.commit()

    filename = f"timetable-llm-export-{inst.slug}-{datetime.utcnow().strftime('%Y%m%d')}.zip"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("", status_code=status.HTTP_202_ACCEPTED)
def delete_institution_data(
    request: Request,
    confirm_slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """
    Hard-delete all data for the caller's institution.

    The caller must pass `?confirm_slug=<institution-slug>` that matches their
    institution, as a footgun guard. All tenant-scoped rows are deleted; the
    Institution row itself is kept but marked inactive so audit trails survive.
    """
    iid = current_user.institution_id
    inst = db.query(Institution).filter(Institution.id == iid).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")
    if confirm_slug != inst.slug:
        raise HTTPException(
            status_code=400,
            detail=f"confirm_slug mismatch; pass '{inst.slug}' to confirm.",
        )

    # Delete in FK-safe order.
    db.query(TimetableSlot).filter(TimetableSlot.institution_id == iid).delete(synchronize_session=False)
    db.query(Assignment).filter(Assignment.institution_id == iid).delete(synchronize_session=False)
    db.query(Faculty).filter(Faculty.institution_id == iid).delete(synchronize_session=False)
    db.query(Subject).filter(Subject.institution_id == iid).delete(synchronize_session=False)
    db.query(Room).filter(Room.institution_id == iid).delete(synchronize_session=False)
    db.query(Batch).filter(Batch.institution_id == iid).delete(synchronize_session=False)
    db.query(Invite).filter(Invite.institution_id == iid).delete(synchronize_session=False)
    db.query(ScheduleConfig).filter(ScheduleConfig.institution_id == iid).delete(synchronize_session=False)
    # Users deleted last because audit logs reference them.
    db.query(User).filter(User.institution_id == iid, User.id != current_user.id).delete(synchronize_session=False)

    inst.is_active = False
    db.commit()

    # Record the erasure in the immutable-ish audit table. The caller's own
    # user row stays so this entry has a valid user_id reference.
    log_action(
        db=db,
        institution_id=iid,
        user_id=current_user.id,
        action="institution.erase",
        entity_type="institution",
        entity_id=str(iid),
        details={"requested_by": current_user.email},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    # Retain audit log for compliance — do NOT delete AuditLog rows here.
    _ = db.query(AuditLog).filter(AuditLog.institution_id == iid).count()

    return {
        "status": "erased",
        "institution_id": iid,
        "note": "Tenant data removed. AuditLog entries retained for compliance.",
    }
