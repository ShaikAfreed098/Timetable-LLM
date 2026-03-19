from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.subject import Subject
from app.schemas.subject import SubjectCreate, SubjectUpdate, SubjectOut
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


@router.get("", response_model=List[SubjectOut])
def list_subjects(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Subject).all()


@router.post("", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
def add_subject(
    subject_in: SubjectCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    if db.query(Subject).filter(Subject.code == subject_in.code).first():
        raise HTTPException(status_code=400, detail="Subject code already exists.")
    subject = Subject(**subject_in.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.get("/{subject_id}", response_model=SubjectOut)
def get_subject(
    subject_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)
):
    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found.")
    return subject


@router.put("/{subject_id}", response_model=SubjectOut)
def update_subject(
    subject_id: int,
    subject_in: SubjectUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found.")
    for key, value in subject_in.model_dump(exclude_unset=True).items():
        setattr(subject, key, value)
    db.commit()
    db.refresh(subject)
    return subject


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)
):
    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found.")
    db.delete(subject)
    db.commit()
