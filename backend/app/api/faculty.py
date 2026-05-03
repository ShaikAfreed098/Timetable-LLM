from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.faculty import Faculty
from app.models.user import User
from app.schemas.faculty import FacultyCreate, FacultyUpdate, FacultyOut
from app.core.auth import get_current_user, require_role, require_department_scope

router = APIRouter(prefix="/api/faculty", tags=["faculty"])


@router.get("", response_model=List[FacultyOut])
def list_faculty(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Faculty).filter(Faculty.institution_id == current_user.institution_id).all()


@router.post("", response_model=FacultyOut, status_code=status.HTTP_201_CREATED)
def add_faculty(
    faculty_in: FacultyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "department_admin")),
):
    require_department_scope(current_user, faculty_in.department)
    if db.query(Faculty).filter(Faculty.email == faculty_in.email, Faculty.institution_id == current_user.institution_id).first():
        raise HTTPException(status_code=400, detail="Faculty email already exists.")
    faculty = Faculty(**faculty_in.model_dump(), institution_id=current_user.institution_id)
    db.add(faculty)
    db.commit()
    db.refresh(faculty)
    return faculty


@router.get("/{faculty_id}", response_model=FacultyOut)
def get_faculty(
    faculty_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id, Faculty.institution_id == current_user.institution_id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found.")
    return faculty


@router.put("/{faculty_id}", response_model=FacultyOut)
def update_faculty(
    faculty_id: int,
    faculty_in: FacultyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "department_admin")),
):
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id, Faculty.institution_id == current_user.institution_id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found.")
    require_department_scope(current_user, faculty.department)
    for key, value in faculty_in.model_dump(exclude_unset=True).items():
        setattr(faculty, key, value)
    db.commit()
    db.refresh(faculty)
    return faculty


@router.delete("/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faculty(
    faculty_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role("super_admin", "department_admin"))
):
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id, Faculty.institution_id == current_user.institution_id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found.")
    require_department_scope(current_user, faculty.department)
    db.delete(faculty)
    db.commit()


@router.get("/{faculty_id}/schedule")
def get_faculty_schedule(
    faculty_id: int,
    timetable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.timetable import TimetableSlot
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id, Faculty.institution_id == current_user.institution_id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found.")
    slots = (
        db.query(TimetableSlot)
        .filter(
            TimetableSlot.timetable_id == timetable_id,
            TimetableSlot.faculty_id == faculty_id,
            TimetableSlot.institution_id == current_user.institution_id,
        )
        .all()
    )
    return {"faculty": FacultyOut.model_validate(faculty), "slots": slots}
