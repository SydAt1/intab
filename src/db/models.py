from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    reset_token = Column(String(255), nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)

    audio_files = relationship("AudioFile", back_populates="user")

import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Boolean, JSON, ForeignKey

class QuizSession(Base):
    __tablename__ = "quiz_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id")) # using Integer because users.id is Integer
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    final_score = Column(Integer, default=0)
    final_streak = Column(Integer, default=0)
    difficulty_reached = Column(String)  # "beginner" | "intermediate" | "advanced"

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("quiz_sessions.id"))
    question_number = Column(Integer)
    chord_shown = Column(String)
    options = Column(JSON)           # list of 4 label strings
    user_answer = Column(String)
    is_correct = Column(Boolean)
    difficulty = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Late import to ensure AudioFile is registered in SQLAlchemy when queries run
from src.db.audio_model import AudioFile
