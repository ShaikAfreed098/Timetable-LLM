from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.models.user import User
from app.models.invite import Invite
from app.schemas.user import UserCreate, UserOut, Token
from app.core.auth import get_current_user, create_access_token
from app.config import settings
from firebase_admin import auth as firebase_auth
from passlib.context import CryptContext
import secrets
from app.tasks import send_email
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
limiter = Limiter(key_func=get_remote_address)

class FirebaseToken(BaseModel):
    token: str

@router.post("/google", response_model=Token)
@limiter.limit("10/minute")
def login_google(request: Request, firebase_token: FirebaseToken, response: Response, db: Session = Depends(get_db)):
    try:
        payload = firebase_auth.verify_id_token(firebase_token.token)
        email = payload.get("email")
        firebase_uid = payload.get("uid")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Firebase token: {e}")

    if not email:
        raise HTTPException(status_code=400, detail="Token does not contain an email")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Check for invite
        invite = db.query(Invite).filter(Invite.email == email, Invite.used_at.is_(None)).first()
        if not invite or invite.expires_at < datetime.utcnow():
            raise HTTPException(status_code=403, detail="No valid invite found for this email")
        
        # Create user
        is_new_firebase_user = user is None
        try:
            user = User(
                institution_id=invite.institution_id,
                username=email.split("@")[0],
                email=email,
                firebase_uid=firebase_uid,
                hashed_password="firebase-managed",
                role=invite.role,
            )
            db.add(user)
            invite.used_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            if is_new_firebase_user:
                try:
                    firebase_auth.delete_user(firebase_uid)
                except Exception as fb_err:
                    logger.exception(
                        "Failed to roll back Firebase user %s after DB failure: %s",
                        firebase_uid, fb_err,
                    )
            raise HTTPException(status_code=500, detail="Failed to create user account")

    # Issue our JWT
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "institution_id": user.institution_id}, expires_delta=access_token_expires
    )
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=not settings.DEBUG,
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
def login_for_access_token(request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    if user.hashed_password != "firebase-managed":
        if not pwd_context.verify(form_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect username or password")
    else:
        # User is firebase-managed, password login is disabled for them
        raise HTTPException(status_code=400, detail="Please login using Google")

    access_token_expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "institution_id": user.institution_id}, expires_delta=access_token_expires
    )
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=not settings.DEBUG,
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token", samesite="lax", secure=not settings.DEBUG)
    return {"message": "Logged out successfully"}


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, request: Request, db: Session = Depends(get_db)):
    if not settings.BOOTSTRAP_TOKEN:
        raise HTTPException(status_code=404, detail="Not Found")
    
    bootstrap_token = request.headers.get("X-Bootstrap-Token")
    if not bootstrap_token or bootstrap_token != settings.BOOTSTRAP_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already taken.")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    
    if not user_in.institution_id:
        raise HTTPException(status_code=400, detail="institution_id is required")

    # We no longer rely on the local password for auth (Firebase handles it),
    # but the DB schema requires something.
    hashed = pwd_context.hash(user_in.password) if user_in.password else "firebase-managed"
    user = User(
        institution_id=user_in.institution_id,
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed,
        role=user_in.role,
        department=user_in.department,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user


class ForgotPasswordRequest(BaseModel):
    email: str


@router.post("/forgot-password")
@limiter.limit("3/hour")
def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        # Avoid user enumeration by returning 200 even if email not found
        return {"message": "If an account exists with this email, a reset link has been sent."}

    if user.hashed_password == "firebase-managed":
        return {"message": "Please use Google to sign in to this account."}

    # Reuse Invite model for password reset
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    # Delete any existing password reset invites for this email
    db.query(Invite).filter(Invite.email == body.email, Invite.purpose == "password_reset").delete()
    
    reset_invite = Invite(
        institution_id=user.institution_id,
        email=user.email,
        role=user.role,
        token=token,
        purpose="password_reset",
        expires_at=expires_at
    )
    db.add(reset_invite)
    db.commit()
    
    reset_url = f"{settings.ALLOWED_ORIGINS.split(',')[0]}/reset-password?token={token}"
    send_email.delay(
        to_email=user.email,
        subject="Password Reset Request",
        body=f"You requested a password reset. Click here to reset: {reset_url}\n\nIf you did not request this, please ignore this email."
    )
    
    return {"message": "If an account exists with this email, a reset link has been sent."}


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)):
    reset_invite = db.query(Invite).filter(
        Invite.token == body.token, 
        Invite.purpose == "password_reset",
        Invite.used_at.is_(None)
    ).first()
    
    if not reset_invite or reset_invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
    user = db.query(User).filter(User.email == reset_invite.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.hashed_password = pwd_context.hash(body.new_password)
    reset_invite.used_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Password updated successfully"}
