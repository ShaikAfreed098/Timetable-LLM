from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.room import Room
from app.models.user import User
from app.schemas.room import RoomCreate, RoomUpdate, RoomOut
from app.core.auth import get_current_user, require_role

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


@router.get("", response_model=List[RoomOut])
def list_rooms(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Room).filter(Room.institution_id == current_user.institution_id).all()


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def add_room(
    room_in: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "department_admin")),
):
    if db.query(Room).filter(Room.room_number == room_in.room_number, Room.institution_id == current_user.institution_id).first():
        raise HTTPException(status_code=400, detail="Room number already exists.")
    room = Room(**room_in.model_dump(), institution_id=current_user.institution_id)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.get("/{room_id}", response_model=RoomOut)
def get_room(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    room = db.query(Room).filter(Room.id == room_id, Room.institution_id == current_user.institution_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found.")
    return room


@router.put("/{room_id}", response_model=RoomOut)
def update_room(
    room_id: int,
    room_in: RoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "department_admin")),
):
    room = db.query(Room).filter(Room.id == room_id, Room.institution_id == current_user.institution_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found.")
    for key, value in room_in.model_dump(exclude_unset=True).items():
        setattr(room, key, value)
    db.commit()
    db.refresh(room)
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role("super_admin", "department_admin"))
):
    room = db.query(Room).filter(Room.id == room_id, Room.institution_id == current_user.institution_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found.")
    db.delete(room)
    db.commit()
