from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.batch import Batch
from app.models.user import User
from app.schemas.batch import BatchCreate, BatchUpdate, BatchOut
from app.core.auth import get_current_user, require_role, require_department_scope

router = APIRouter(prefix="/api/batches", tags=["batches"])


@router.get("", response_model=List[BatchOut])
def list_batches(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Batch).filter(Batch.institution_id == current_user.institution_id).all()


@router.post("", response_model=BatchOut, status_code=status.HTTP_201_CREATED)
def add_batch(
    batch_in: BatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "department_admin")),
):
    require_department_scope(current_user, batch_in.department)
    batch = Batch(**batch_in.model_dump(), institution_id=current_user.institution_id)
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


@router.get("/{batch_id}", response_model=BatchOut)
def get_batch(
    batch_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    batch = db.query(Batch).filter(Batch.id == batch_id, Batch.institution_id == current_user.institution_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    return batch


@router.put("/{batch_id}", response_model=BatchOut)
def update_batch(
    batch_id: int,
    batch_in: BatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "department_admin")),
):
    batch = db.query(Batch).filter(Batch.id == batch_id, Batch.institution_id == current_user.institution_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    require_department_scope(current_user, batch.department)
    for key, value in batch_in.model_dump(exclude_unset=True).items():
        setattr(batch, key, value)
    db.commit()
    db.refresh(batch)
    return batch


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(
    batch_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role("super_admin", "department_admin"))
):
    batch = db.query(Batch).filter(Batch.id == batch_id, Batch.institution_id == current_user.institution_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    require_department_scope(current_user, batch.department)
    db.delete(batch)
    db.commit()
