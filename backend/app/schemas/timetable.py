from pydantic import BaseModel
from typing import Optional, List
from app.schemas.faculty import FacultyOut
from app.schemas.subject import SubjectOut
from app.schemas.room import RoomOut
from app.schemas.batch import BatchOut


class AssignmentCreate(BaseModel):
    faculty_id: int
    subject_id: int
    batch_id: int
    semester: int


class AssignmentOut(BaseModel):
    id: int
    faculty_id: int
    subject_id: int
    batch_id: int
    semester: int
    faculty: Optional[FacultyOut] = None
    subject: Optional[SubjectOut] = None
    batch: Optional[BatchOut] = None

    model_config = {"from_attributes": True}


class TimetableSlotOut(BaseModel):
    id: int
    timetable_id: str
    batch_id: int
    day_of_week: str
    period_number: int
    subject_id: Optional[int] = None
    faculty_id: Optional[int] = None
    room_id: Optional[int] = None
    slot_type: str
    subject: Optional[SubjectOut] = None
    faculty: Optional[FacultyOut] = None
    room: Optional[RoomOut] = None

    model_config = {"from_attributes": True}


class TimetableOut(BaseModel):
    timetable_id: str
    batch: BatchOut
    slots: List[TimetableSlotOut]
    conflicts: List[str] = []
