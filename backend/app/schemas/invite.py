from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class InviteCreate(BaseModel):
    email: EmailStr
    role: str

class InviteOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    token: str
    expires_at: datetime
    used_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class InviteAccept(BaseModel):
    # This might take a password if not using Google Auth
    password: Optional[str] = None
