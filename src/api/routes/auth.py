from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Optional
from sqlalchemy.orm import Session
from src.db.connection import get_db
from src.db.models import User
from src.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from src.auth.password_utils import hash_password, verify_password
from src.auth.jwt_utils import create_access_token
from src.api.dependencies import get_current_user
from src.util.sessionHandler import session_manager
from src.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse, ForgotPasswordRequest, ResetPasswordRequest
from src.util.email import send_reset_email

import uuid
import secrets
from datetime import datetime, timedelta

router = APIRouter(prefix="", tags=["auth"])

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # We don't want to reveal if an email is registered or not for security
        return {"message": "If an account with this email exists, a reset link has been sent."}
    
    # Generate random token
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
    
    db.commit()
    
    # Send email
    sent = send_reset_email(user.email, token)
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send reset email")
        
    return {"message": "If an account with this email exists, a reset link has been sent."}

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.reset_token == request.token,
        User.reset_token_expiry > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Update password
    user.password_hash = hash_password(request.new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    
    db.commit()
    
    return {"message": "Password reset successfully"}

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create new user
    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/login", response_model=TokenResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Generate Token and Session ID
    access_token = create_access_token(data={"sub": db_user.username})
    session_id = str(uuid.uuid4())
    
    # Create and store session
    session_manager.create_session(session_id, db_user.username)
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "session_id": session_id,
        "user": db_user
    }

from src.util.sessionHandler import require_session

@router.get("/me")
async def read_users_me(
    current_user: User = Depends(get_current_user),
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id")
):
    session = session_manager.get_session(x_session_id) if x_session_id else None
    if session:
        return {"username": session["username"], "is_active": True}
    return current_user

@router.post("/logout")
async def logout(session: dict = Depends(require_session)):
    """
    Logout endpoint that invalidates the user's session.
    Requires valid X-Session-Id header.
    """
    # The session dict contains session_id from require_session dependency
    session_id = session.get("session_id")
    if session_id:
        session_manager.delete_session(session_id)
    
    return {"message": "Logged out successfully"}
