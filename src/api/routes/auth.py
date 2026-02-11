from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.db.connection import get_db
from src.db.models import User
from src.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from src.auth.password_utils import hash_password, verify_password
from src.auth.jwt_utils import create_access_token
from src.api.dependencies import get_current_user
from src.util.sessionHandler import session_manager

import uuid

router = APIRouter(prefix="", tags=["auth"])

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

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
