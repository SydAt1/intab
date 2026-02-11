# src/util/sessionHandler.py

from fastapi import HTTPException, status, Header
from typing import Optional, Dict
import time


class SessionManager:
    """
    Simple in-memory session storage.
    Replace with Redis or DB in production.
    """

    def __init__(self):
        # session_id -> {username, created_at}
        self.active_sessions: Dict[str, dict] = {}

    def create_session(self, session_id: str, username: str):
        self.active_sessions[session_id] = {
            "username": username,
            "created_at": time.time()
        }

    def get_session(self, session_id: str):
        return self.active_sessions.get(session_id)

    def delete_session(self, session_id: str):
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

    def validate_session(self, session_id: str):
        session = self.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session"
            )
        return session


# Create global session manager instance
session_manager = SessionManager()


# Dependency to require valid session
def require_session(x_session_id: Optional[str] = Header(None)):
    """
    Expects session ID in header:
    X-Session-Id: <session_id>
    """
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session ID missing"
        )

    session_data = session_manager.validate_session(x_session_id)
    # Add the session_id to the returned dict for logout endpoint
    session_data["session_id"] = x_session_id
    return session_data
