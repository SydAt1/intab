from fastapi import Depends
from src.api.dependencies import get_current_user
from src.db.models import User

async def require_login(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that ensures a user is logged in.
    Re-uses the existing get_current_user logic which validates the JWT token.
    Raises 401 if invalid or missing.
    """
    return current_user
