"""
Quota API Routes

Provides endpoints for:
- Listing available models from cloudcode-pa
- Querying account quota/usage
- Account pool status
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import httpx

from app.core.token_manager import get_token_manager

router = APIRouter()

CLOUD_CODE_URL = "https://cloudcode-pa.googleapis.com/v1internal"


@router.get("/models")
async def list_available_models() -> Dict[str, Any]:
    """
    Fetch available models from cloudcode-pa API.
    
    Returns list of all models available for the current account.
    """
    token_manager = get_token_manager()
    
    try:
        access_token, project_id, email = await token_manager.get_token()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    url = f"{CLOUD_CODE_URL}:fetchAvailableModels"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "antigravity/python/1.0",
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json={}, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", {})
                
                return {
                    "account_email": email,
                    "project_id": project_id,
                    "total_models": len(models),
                    "models": list(models.keys()),
                }
            else:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Upstream error: {response.text}"
                )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Request failed: {e}")


@router.get("/pool")
async def get_account_pool_status() -> Dict[str, Any]:
    """
    Get the status of the account pool.
    
    Returns information about all accounts loaded in TokenManager.
    """
    token_manager = get_token_manager()
    
    return {
        "pool_size": token_manager.pool_size,
        "accounts": token_manager.get_all_accounts(),
    }


@router.post("/pool/reload")
async def reload_account_pool() -> Dict[str, Any]:
    """
    Reload all accounts from database into TokenManager.
    
    Use this after adding new accounts via OAuth or import.
    """
    token_manager = get_token_manager()
    count = await token_manager.load_accounts()
    
    return {
        "status": "success",
        "accounts_loaded": count,
    }


@router.get("/quota/{model_name}")
async def get_model_quota(model_name: str) -> Dict[str, Any]:
    """
    Get quota information for a specific model (if available).
    
    Note: Quota data availability depends on account type.
    """
    token_manager = get_token_manager()
    
    try:
        access_token, project_id, email = await token_manager.get_token()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    url = f"{CLOUD_CODE_URL}:fetchAvailableModels"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "antigravity/python/1.0",
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json={"project": project_id}, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", {})
                
                if model_name in models:
                    model_info = models[model_name]
                    quota_info = model_info.get("quotaInfo", {})
                    
                    return {
                        "model": model_name,
                        "account_email": email,
                        "remaining_fraction": quota_info.get("remainingFraction"),
                        "reset_time": quota_info.get("resetTime"),
                        "description": model_info.get("description"),
                    }
                else:
                    return {
                        "model": model_name,
                        "account_email": email,
                        "status": "not_found",
                        "available_models": list(models.keys())[:10],
                    }
            else:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Upstream error: {response.text}"
                )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Request failed: {e}")
@router.get("/matrix")
async def get_quota_matrix() -> List[Dict[str, Any]]:
    """
    Get quota information for ALL accounts across model groups.
    
    Groups:
    - Claude/GPT: claude-sonnet-4-5-thinking (Shared with gpt-oss)
    - Gemini Pro: gemini-3-pro-high (Shared with low)
    - Gemini Flash: gemini-3-flash (Independent)
    """
    token_manager = get_token_manager()
    
    # We iterate over all accounts directly from the manager
    # Accessing private member _tokens is acceptable here as we are in the same app context
    # ideally we would add a public getter, but for now this works.
    tokens = list(token_manager._tokens.values())
    
    results = []
    
    # Representative models for each group
    # Note: Using hardcoded representatives as per user logic
    groups = {
        "claude_gpt": "claude-sonnet-4-5-thinking",
        "gemini_pro": "gemini-3-pro-high",
        "gemini_flash": "gemini-3-flash"
    }
    
    for token in tokens:
        account_status = {
            "email": token.email,
            "project_id": token.project_id,
            "quotas": {}
        }
        
        # Prepare client for this account
        headers = {
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "antigravity/python/1.0",
        }
        
        # We need to fetch the models list ONCE for this account to get all quotas
        # Instead of 3 calls, we call fetchAvailableModels once and parse the dict
        url = f"{CLOUD_CODE_URL}:fetchAvailableModels"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json={"project": token.project_id}, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    models_data = data.get("models", {})
                    
                    for group_key, model_name in groups.items():
                        if model_name in models_data:
                            info = models_data[model_name].get("quotaInfo", {})
                            account_status["quotas"][group_key] = {
                                "model": model_name,
                                "remaining_fraction": info.get("remainingFraction"),
                                "reset_time": info.get("resetTime"),
                                "available": True
                            }
                        else:
                             account_status["quotas"][group_key] = {
                                "model": model_name,
                                "available": False,
                                "reason": "Not found in account"
                            }
                else:
                    account_status["error"] = f"Upstream {response.status_code}"
        except Exception as e:
            account_status["error"] = str(e)
            
        results.append(account_status)
        
    return results


@router.get("/best-account")
async def get_best_account() -> Dict[str, Any]:
    """
    Calculate and return the best account based on average remaining quota.
    
    Algorithm:
    - For each account, compute the average remaining_fraction across all model groups
    - Return the account with the highest average
    """
    matrix = await get_quota_matrix()
    
    if not matrix:
        return {"best_account": None, "average_quota": 0, "all_averages": []}
    
    accounts_with_avg = []
    
    for account in matrix:
        if "error" in account:
            continue
            
        quotas = account.get("quotas", {})
        fractions = []
        
        for group_key, quota_info in quotas.items():
            if quota_info.get("available") and quota_info.get("remaining_fraction") is not None:
                fractions.append(quota_info["remaining_fraction"])
        
        if fractions:
            avg = sum(fractions) / len(fractions)
            accounts_with_avg.append({
                "email": account["email"],
                "project_id": account["project_id"],
                "average_quota": round(avg, 4),
                "quotas": quotas
            })
    
    if not accounts_with_avg:
        return {"best_account": None, "average_quota": 0, "all_averages": []}
    
    # Sort by average quota descending
    accounts_with_avg.sort(key=lambda x: x["average_quota"], reverse=True)
    
    best = accounts_with_avg[0]
    
    # Calculate overall average across all accounts
    overall_avg = sum(a["average_quota"] for a in accounts_with_avg) / len(accounts_with_avg)
    
    return {
        "best_account": {
            "email": best["email"],
            "project_id": best["project_id"],
            "average_quota": best["average_quota"]
        },
        "overall_average": round(overall_avg, 4),
        "all_accounts": accounts_with_avg
    }

