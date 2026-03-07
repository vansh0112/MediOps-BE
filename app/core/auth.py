"""JWT authentication for Supabase Auth tokens."""

import os
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Supabase JWT secret from Supabase Dashboard > Project Settings > API > JWT Secret
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "").strip()
# Audience for user tokens (Supabase uses "authenticated" for authenticated users)
JWT_AUDIENCE = "authenticated"
JWT_ALGORITHMS = ["HS256"]

security = HTTPBearer(auto_error=False)


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    """
    Verify Supabase JWT and return decoded payload.
    Use as dependency: Depends(get_current_user)
    """
    if not JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth not configured: SUPABASE_JWT_SECRET missing",
        )

    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            cred.credentials,
            JWT_SECRET,
            audience=JWT_AUDIENCE,
            algorithms=JWT_ALGORITHMS,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Require authenticated role (reject anon tokens)
    if payload.get("role") != "authenticated":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token role",
        )

    return payload


def get_current_user_optional(
    cred: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any] | None:
    """
    Same as get_current_user but returns None if no/invalid token.
    Use for endpoints that work both authenticated and unauthenticated.
    """
    if not JWT_SECRET or cred is None:
        return None

    try:
        payload = jwt.decode(
            cred.credentials,
            JWT_SECRET,
            audience=JWT_AUDIENCE,
            algorithms=JWT_ALGORITHMS,
        )
        if payload.get("role") == "authenticated":
            return payload
    except jwt.PyJWTError:
        pass
    return None
