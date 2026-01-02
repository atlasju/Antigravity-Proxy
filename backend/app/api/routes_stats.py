"""
Stats API Routes

Provides aggregated statistics for system usage analytics.
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from datetime import datetime, timedelta
from typing import Dict, List, Any

from app.core.database import get_session
from app.models.usage import UsageLog
from app.core.token_manager import get_token_manager

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/overview")
async def get_overview(session: Session = Depends(get_session)) -> Dict[str, Any]:
    """Get overall statistics: total requests, success rate, avg response time."""
    # Total requests
    total = session.exec(select(func.count(UsageLog.id))).one()
    
    # Success count
    success_count = session.exec(
        select(func.count(UsageLog.id)).where(UsageLog.success == True)
    ).one()
    
    # Average response time
    avg_time = session.exec(
        select(func.avg(UsageLog.response_time_ms))
    ).one()
    
    # Today's requests
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = session.exec(
        select(func.count(UsageLog.id)).where(UsageLog.timestamp >= today)
    ).one()
    
    return {
        "total_requests": total or 0,
        "success_rate": round((success_count / total * 100) if total else 0, 1),
        "avg_response_time_ms": round(avg_time or 0, 0),
        "today_requests": today_count or 0
    }


@router.get("/protocols")
async def get_protocol_stats(session: Session = Depends(get_session)) -> List[Dict[str, Any]]:
    """Get request count by protocol (OpenAI, Claude, Gemini, ImageGen)."""
    results = session.exec(
        select(UsageLog.protocol, func.count(UsageLog.id).label("count"))
        .group_by(UsageLog.protocol)
    ).all()
    
    protocol_names = {
        "openai": "OpenAI",
        "claude": "Claude",
        "gemini": "Gemini",
        "image_gen": "Image Gen"
    }
    
    return [
        {"name": protocol_names.get(r[0], r[0]), "value": r[1]}
        for r in results
    ]


@router.get("/accounts")
async def get_account_stats(session: Session = Depends(get_session)) -> List[Dict[str, Any]]:
    """Get request count per account."""
    results = session.exec(
        select(UsageLog.account_email, func.count(UsageLog.id).label("count"))
        .group_by(UsageLog.account_email)
        .order_by(func.count(UsageLog.id).desc())
        .limit(10)
    ).all()
    
    return [
        {"email": r[0], "requests": r[1]}
        for r in results
    ]


@router.get("/models")
async def get_model_stats(session: Session = Depends(get_session)) -> List[Dict[str, Any]]:
    """Get top 10 most used models."""
    results = session.exec(
        select(UsageLog.model, func.count(UsageLog.id).label("count"))
        .group_by(UsageLog.model)
        .order_by(func.count(UsageLog.id).desc())
        .limit(10)
    ).all()
    
    max_count = results[0][1] if results else 1
    
    return [
        {"model": r[0], "count": r[1], "percentage": round(r[1] / max_count * 100)}
        for r in results
    ]


@router.get("/daily")
async def get_daily_stats(session: Session = Depends(get_session)) -> List[Dict[str, Any]]:
    """Get daily request counts for the last 7 days."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today - timedelta(days=6)
    
    # Generate all 7 days
    days = []
    for i in range(7):
        day = start_date + timedelta(days=i)
        next_day = day + timedelta(days=1)
        
        count = session.exec(
            select(func.count(UsageLog.id))
            .where(UsageLog.timestamp >= day)
            .where(UsageLog.timestamp < next_day)
        ).one()
        
        days.append({
            "date": day.strftime("%m/%d"),
            "requests": count or 0
        })
    
    return days


@router.get("/errors")
async def get_error_stats(session: Session = Depends(get_session)) -> List[Dict[str, Any]]:
    """Get error breakdown by type."""
    results = session.exec(
        select(UsageLog.error_type, func.count(UsageLog.id).label("count"))
        .where(UsageLog.error_type != None)
        .group_by(UsageLog.error_type)
        .order_by(func.count(UsageLog.id).desc())
    ).all()
    
    error_names = {
        "429": "Rate Limit (429)",
        "403": "Forbidden (403)",
        "5xx": "Server Error (5xx)",
        "network": "Network Error"
    }
    
    return [
        {"type": error_names.get(r[0], r[0]), "count": r[1]}
        for r in results
    ]


@router.get("/quotas")
async def get_quota_stats() -> List[Dict[str, Any]]:
    """Get current quota status for all accounts."""
    token_manager = get_token_manager()
    
    result = []
    for account_id, token in token_manager._tokens.items():
        result.append({
            "email": token.email,
            "tier": token.subscription_tier or "unknown",
            "quota": round(token.average_quota * 100) if token.average_quota else 0
        })
    
    # Sort by quota descending
    result.sort(key=lambda x: x["quota"], reverse=True)
    return result
