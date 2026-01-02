"""
Usage Log Model

Records each API request for statistics tracking.
"""
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class UsageLog(SQLModel, table=True):
    """Log entry for each API request."""
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Request info
    protocol: str  # "openai", "claude", "gemini", "image_gen"
    model: str
    account_email: str
    
    # Response info
    success: bool
    status_code: int
    response_time_ms: int
    
    # Error classification (if any)
    error_type: Optional[str] = None  # "429", "403", "5xx", "network", None


class UsageLogCreate(SQLModel):
    """Schema for creating a usage log entry."""
    protocol: str
    model: str
    account_email: str
    success: bool
    status_code: int
    response_time_ms: int
    error_type: Optional[str] = None
