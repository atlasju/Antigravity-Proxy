"""
Authentication Utilities

JWT token creation/validation and FastAPI dependencies.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.core.database import engine
from app.models.user import User

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "antigravity-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Security scheme
security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username from database."""
    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        return session.exec(statement).first()


def get_user_by_api_key(api_key: str) -> Optional[User]:
    """Get user by API key from database."""
    with Session(engine) as session:
        statement = select(User).where(User.api_key == api_key)
        return session.exec(statement).first()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """
    FastAPI dependency to get the current authenticated user.
    
    Supports both:
    - JWT Bearer token (for frontend sessions)
    - API Key (for programmatic access)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    token = credentials.credentials
    
    # First, try to verify as JWT
    payload = verify_token(token)
    if payload:
        username = payload.get("sub")
        if username:
            user = get_user_by_username(username)
            if user:
                return user
    
    # If JWT fails, try as API key
    user = get_user_by_api_key(token)
    if user:
        return user
    
    raise credentials_exception


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Optional auth - returns None if not authenticated.
    Used for routes that work both authenticated and unauthenticated.
    """
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
