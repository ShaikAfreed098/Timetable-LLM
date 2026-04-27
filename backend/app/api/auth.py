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

    # Issue our JWT
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
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
        data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
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
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already taken.")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    
    # Find the default institution (first one)
    from app.models.institution import Institution
    default_inst = db.query(Institution).first()
    if not default_inst:
        raise HTTPException(status_code=500, detail="No institution configured. Please contact admin.")

    # We no longer rely on the local password for auth (Firebase handles it),
    # but the DB schema requires something.
    hashed = pwd_context.hash(user_in.password) if user_in.password else "firebase-managed"
    user = User(
        institution_id=default_inst.id,
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
