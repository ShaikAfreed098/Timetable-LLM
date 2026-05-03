from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets

from app.database import get_db
from app.models.user import User
from app.models.invite import Invite
from app.schemas.invite import InviteCreate, InviteOut, InviteAccept
from app.core.auth import require_role
from passlib.context import CryptContext
from app.config import settings
from app.tasks import send_email

router = APIRouter(prefix="/api/invites", tags=["invites"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
def create_invite(
    invite_in: InviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "department_admin"))
):
    # Ensure no active invite exists for this email
    existing_invite = db.query(Invite).filter(Invite.email == invite_in.email, Invite.used_at.is_(None)).first()
    if existing_invite:
        if existing_invite.expires_at > datetime.utcnow():
            raise HTTPException(status_code=400, detail="Active invite already exists for this email")

    # Ensure user does not already exist
    if db.query(User).filter(User.email == invite_in.email).first():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)

    invite = Invite(
        institution_id=current_user.institution_id,
        email=invite_in.email,
        role=invite_in.role,
        token=token,
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    
    # Send email with token
    invite_url = f"{settings.ALLOWED_ORIGINS.split(',')[0]}/accept-invite?token={token}"
    send_email.delay(
        to_email=invite.email,
        subject=f"Invitation to join {current_user.institution.name}",
        body=f"You have been invited to join {current_user.institution.name} as a {invite.role}.\n\nClick here to accept: {invite_url}"
    )
    
    return invite

@router.post("/{token}/accept", status_code=status.HTTP_200_OK)
def accept_invite(token: str, accept_in: InviteAccept, db: Session = Depends(get_db)):
    invite = db.query(Invite).filter(Invite.token == token, Invite.purpose == "invite", Invite.used_at.is_(None)).first()
    
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found or already used")
        
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invite has expired")

    # If accepting via password (not Firebase Google Auth)
    if accept_in.password:
        if db.query(User).filter(User.email == invite.email).first():
            raise HTTPException(status_code=400, detail="User already exists")
            
        user = User(
            institution_id=invite.institution_id,
            username=invite.email.split("@")[0],
            email=invite.email,
            hashed_password=pwd_context.hash(accept_in.password),
            role=invite.role,
            is_active=True
        )
        db.add(user)
        invite.used_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Invite accepted successfully. You can now login."}
    
    # If using Google auth, the acceptance is handled by /api/auth/google endpoint
    # Here we just validate the token
    return {"message": "Token is valid. Proceed to Google Sign In."}

@router.get("/{token}", response_model=InviteOut)
def get_invite(token: str, db: Session = Depends(get_db)):
    invite = db.query(Invite).filter(Invite.token == token).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    return invite
