from pydantic import BaseModel, EmailStr
from typing import List, Optional, Any


class FacultyBase(BaseModel):
    name: str
    department: str
    email: EmailStr
    max_periods_per_day: int = 5
    preferred_days: List[str] = []
    unavailable_slots: List[Any] = []


class FacultyCreate(FacultyBase):
    pass


class FacultyUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    email: Optional[EmailStr] = None
    max_periods_per_day: Optional[int] = None
    preferred_days: Optional[List[str]] = None
    unavailable_slots: Optional[List[Any]] = None
    is_active: Optional[bool] = None


class FacultyOut(FacultyBase):
    id: int
    is_active: bool

    model_config = {"from_attributes": True}
