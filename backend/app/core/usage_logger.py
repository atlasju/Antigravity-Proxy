"""
Usage Logger

Helper to log API usage statistics asynchronously.
"""
from datetime import datetime
from sqlmodel import Session
from app.core.database import engine
from app.models.usage import UsageLog


def log_usage(
    protocol: str,
    model: str,
    account_email: str,
    success: bool,
    status_code: int,
    response_time_ms: int,
    error_type: str = None
):
    """
    Log an API request to the usage_log table.
    
    Args:
        protocol: "openai", "claude", "gemini", "image_gen"
        model: Model name used
        account_email: Account email used
        success: Whether request succeeded
        status_code: HTTP status code
        response_time_ms: Response time in milliseconds
        error_type: Optional error classification ("429", "403", "5xx", "network")
    """
    try:
        with Session(engine) as session:
            log_entry = UsageLog(
                timestamp=datetime.utcnow(),
                protocol=protocol,
                model=model,
                account_email=account_email,
                success=success,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_type=error_type
            )
            session.add(log_entry)
            session.commit()
    except Exception as e:
        # Don't let logging failures break the API
        print(f"[UsageLogger] Failed to log usage: {e}")
