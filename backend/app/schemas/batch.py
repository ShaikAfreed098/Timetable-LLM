from pydantic import BaseModel
from typing import Optional


class BatchBase(BaseModel):
    name: str
    department: str
    semester: int
    student_count: int = 60
    year: int


class BatchCreate(BatchBase):
    pass


class BatchUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    student_count: Optional[int] = None
    year: Optional[int] = None


class BatchOut(BatchBase):
    id: int

    model_config = {"from_attributes": True}
