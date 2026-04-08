import uuid
import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID

from src.db.connection import get_db
from src.filter.auth_filter import get_current_user
from src.db.models import Base, User  # Existing imports

# Pydantic Schemas

class QuizStartResponse(BaseModel):
    session_id: str
    difficulty: str

class QuizQuestionResponse(BaseModel):
    question_number: int
    difficulty: str
    chord: dict
    options: List[str]

class QuizAnswerRequest(BaseModel):
    session_id: str
    question_number: int
    chord_shown: str
    answer: str
    difficulty: str
    current_score: int
    current_streak: int

class QuizAnswerResponse(BaseModel):
    correct: bool
    score_delta: int
    new_score: int
    new_streak: int
    new_difficulty: str

class QuizEndRequest(BaseModel):
    session_id: str
    final_score: int
    final_streak: int
    difficulty_reached: str

class QuizHistoryResponse(BaseModel):
    id: str
    started_at: datetime
    ended_at: Optional[datetime]
    final_score: int
    final_streak: int
    difficulty_reached: Optional[str]

# ========================
# Quiz Router
# ========================

router = APIRouter(tags=["quiz"])

# Imports needed inside router
from src.db.models import QuizSession, QuizAttempt
from src.quiz.quiz_service import get_question, evaluate_answer, next_difficulty, score_delta

@router.post("/start", response_model=QuizStartResponse)
async def start_quiz(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_session = QuizSession(
        user_id=current_user.id,
        difficulty_reached="beginner"
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return QuizStartResponse(
        session_id=str(new_session.id),
        difficulty="beginner"
    )

@router.get("/question", response_model=QuizQuestionResponse)
async def question(
    difficulty: str,
    question_number: int,
    current_user: User = Depends(get_current_user)
):
    qp = get_question(difficulty)
    return QuizQuestionResponse(
        question_number=question_number,
        difficulty=difficulty,
        chord=qp["chord"],
        options=qp["options"]
    )

@router.post("/answer", response_model=QuizAnswerResponse)
async def answer_question(
    req: QuizAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    correct = evaluate_answer(req.answer, req.chord_shown)
    delta = score_delta(req.difficulty, correct)
    
    new_score = req.current_score + delta
    new_streak = req.current_streak + 1 if correct else 0
    new_diff = next_difficulty(req.difficulty, correct, req.current_streak) # Uses previous streak
    
    attempt = QuizAttempt(
        session_id=uuid.UUID(req.session_id),
        question_number=req.question_number,
        chord_shown=req.chord_shown,
        options=req.dict().get("options", []), # The prompt didn't specify client sends options, but the DB expects them. So let's just log empty or client has to send them. We'll leave it empty.
        user_answer=req.answer,
        is_correct=correct,
        difficulty=req.difficulty
    )
    db.add(attempt)
    db.commit()
    
    return QuizAnswerResponse(
        correct=correct,
        score_delta=delta,
        new_score=new_score,
        new_streak=new_streak,
        new_difficulty=new_diff
    )

@router.post("/end")
async def end_quiz(
    req: QuizEndRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session_row = db.query(QuizSession).filter(
        QuizSession.id == uuid.UUID(req.session_id),
        QuizSession.user_id == current_user.id
    ).first()
    
    if not session_row:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session_row.ended_at = datetime.utcnow()
    session_row.final_score = req.final_score
    session_row.final_streak = req.final_streak
    session_row.difficulty_reached = req.difficulty_reached
    
    db.commit()
    return {"message": "session closed"}

@router.get("/history", response_model=List[QuizHistoryResponse])
async def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sessions = db.query(QuizSession).filter(QuizSession.user_id == current_user.id).order_by(QuizSession.started_at.desc()).all()
    # Serialize UUIDs safely
    res = []
    for s in sessions:
        res.append(QuizHistoryResponse(
            id=str(s.id),
            started_at=s.started_at,
            ended_at=s.ended_at,
            final_score=s.final_score or 0,
            final_streak=s.final_streak or 0,
            difficulty_reached=s.difficulty_reached
        ))
    return res
