from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User
from jose import JWTError, jwt

from app.core.firebase import init_firebase

# Ensure Firebase is initialized
init_firebase()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        token = request.cookies.get("access_token")
        if not token:
            raise credentials_exception

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        inst_id: int = payload.get("institution_id")
        
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # DB Fallback for tokens issued before claims were added
    if role is None or inst_id is None:
        user = db.query(User).filter(User.email == email).first()
        if user is None or not user.is_active:
            raise credentials_exception
        return user
    
    # Fast path: Construct a temporary user object from claims
    # This prevents a DB lookup on every request.
    # Note: If you need a full user object with relationships, you'll still need a query.
    # For RBAC and tenant isolation, these claims are often enough.
    # However, to maintain compatibility with existing code that expects a full model:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(*roles: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {roles}",
            )
        return current_user

    return dependency


def require_department_scope(user: User, entity_department: Optional[str]):
    if user.role == "super_admin":
        return
    if user.role == "department_admin":
        if not entity_department or user.department != entity_department:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized for this department",
            )
