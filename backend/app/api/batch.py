from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.batch import Batch
from app.schemas.batch import BatchCreate, BatchUpdate, BatchOut
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/batches", tags=["batches"])


@router.get("", response_model=List[BatchOut])
def list_batches(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Batch).all()


@router.post("", response_model=BatchOut, status_code=status.HTTP_201_CREATED)
def add_batch(
    batch_in: BatchCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    batch = Batch(**batch_in.model_dump())
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


@router.get("/{batch_id}", response_model=BatchOut)
def get_batch(
    batch_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)
):
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    return batch


@router.put("/{batch_id}", response_model=BatchOut)
def update_batch(
    batch_id: int,
    batch_in: BatchUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    for key, value in batch_in.model_dump(exclude_unset=True).items():
        setattr(batch, key, value)
    db.commit()
    db.refresh(batch)
    return batch


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(
    batch_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)
):
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    db.delete(batch)
    db.commit()
