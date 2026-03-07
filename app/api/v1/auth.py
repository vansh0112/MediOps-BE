"""Auth endpoints."""

from fastapi import APIRouter, Depends, status
from app.core.auth import get_current_user

router = APIRouter(tags=["auth"])


@router.get("/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """
    Return current authenticated user info from JWT.
    Use this to verify token validity and get user id/email.
    """
    return {
        "id": user.get("sub"),
        "email": user.get("email"),
        "role": user.get("role"),
    }
