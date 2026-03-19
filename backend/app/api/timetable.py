from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from typing import List
import io

from app.database import get_db
from app.models.timetable import TimetableSlot, Assignment
from app.models.batch import Batch
from app.schemas.timetable import AssignmentCreate, AssignmentOut, TimetableSlotOut
from app.core.auth import get_current_user
from app.core.scheduler import generate_timetable as _generate, check_conflicts as _check
from app.core.export import export_to_pdf, export_to_excel

router = APIRouter(prefix="/api/timetable", tags=["timetable"])


@router.post("/assignments", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(
    assignment_in: AssignmentCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    existing = (
        db.query(Assignment)
        .filter(
            Assignment.faculty_id == assignment_in.faculty_id,
            Assignment.subject_id == assignment_in.subject_id,
            Assignment.batch_id == assignment_in.batch_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Assignment already exists.")
    a = Assignment(**assignment_in.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.get("/assignments", response_model=List[AssignmentOut])
def list_assignments(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Assignment).all()


@router.post("/generate")
def generate(
    semester: int,
    department: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    result = _generate(db, semester, department)
    if result.get("conflicts") and not result.get("timetable_id"):
        raise HTTPException(status_code=422, detail=result["conflicts"])
    return result


@router.get("/{timetable_id}", response_model=List[TimetableSlotOut])
def get_timetable(
    timetable_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    slots = (
        db.query(TimetableSlot)
        .filter(TimetableSlot.timetable_id == timetable_id)
        .all()
    )
    if not slots:
        raise HTTPException(status_code=404, detail="Timetable not found.")
    return slots


@router.put("/{timetable_id}/slot")
def modify_slot(
    timetable_id: str,
    slot_id: int,
    new_faculty_id: int | None = None,
    new_room_id: int | None = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    slot = (
        db.query(TimetableSlot)
        .filter(
            TimetableSlot.timetable_id == timetable_id,
            TimetableSlot.id == slot_id,
        )
        .first()
    )
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found.")
    if new_faculty_id is not None:
        slot.faculty_id = new_faculty_id
    if new_room_id is not None:
        slot.room_id = new_room_id
    db.commit()
    return {"message": "Slot updated."}


@router.get("/{timetable_id}/conflicts")
def get_conflicts(
    timetable_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    conflicts = _check(db, timetable_id)
    return {"timetable_id": timetable_id, "conflicts": conflicts}


@router.post("/{timetable_id}/export")
def export_timetable(
    timetable_id: str,
    format: str = "pdf",
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    if format == "excel":
        data = export_to_excel(db, timetable_id)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=timetable_{timetable_id}.xlsx"},
        )
    else:
        data = export_to_pdf(db, timetable_id)
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=timetable_{timetable_id}.pdf"},
        )
