from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "department_admin"
    department: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    department: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
