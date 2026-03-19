from pydantic import BaseModel
from typing import Optional


class SubjectBase(BaseModel):
    name: str
    code: str
    department: str
    credits: int = 3
    periods_per_week: int = 3
    requires_lab: bool = False


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    department: Optional[str] = None
    credits: Optional[int] = None
    periods_per_week: Optional[int] = None
    requires_lab: Optional[bool] = None


class SubjectOut(SubjectBase):
    id: int

    model_config = {"from_attributes": True}
