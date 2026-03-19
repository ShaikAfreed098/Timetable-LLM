from pydantic import BaseModel
from typing import Optional
from app.models.room import RoomType


class RoomBase(BaseModel):
    room_number: str
    capacity: int = 60
    type: RoomType = RoomType.classroom
    floor: int = 1
    building: str = "Main"


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    room_number: Optional[str] = None
    capacity: Optional[int] = None
    type: Optional[RoomType] = None
    floor: Optional[int] = None
    building: Optional[str] = None


class RoomOut(RoomBase):
    id: int

    model_config = {"from_attributes": True}
