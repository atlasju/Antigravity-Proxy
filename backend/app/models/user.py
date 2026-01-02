"""
User Model

Stores user credentials and API keys for authentication.
"""
import secrets
import hashlib
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash."""
    try:
        salt, hashed = stored_hash.split(":")
        check = hashlib.sha256((salt + password).encode()).hexdigest()
        return check == hashed
    except ValueError:
        return False


class User(SQLModel, table=True):
    """User model for authentication."""
    id: Optional[str] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    api_key: str = Field(default_factory=lambda: f"sk-ag-{secrets.token_urlsafe(32)}")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @classmethod
    def create(cls, username: str, password: str) -> "User":
        """Create a new user with hashed password."""
        import uuid
        return cls(
            id=str(uuid.uuid4()),
            username=username,
            hashed_password=hash_password(password),
        )
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        return verify_password(password, self.hashed_password)
    
    def regenerate_api_key(self) -> str:
        """Generate a new API key."""
        self.api_key = f"sk-ag-{secrets.token_urlsafe(32)}"
        return self.api_key


class UserLogin(SQLModel):
    """Login request schema."""
    username: str
    password: str


class UserResponse(SQLModel):
    """User response schema (without sensitive fields)."""
    id: str
    username: str
    api_key: str
    created_at: datetime
