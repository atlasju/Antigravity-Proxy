"""
Gemini Native Protocol API Routes

Exposes Google Gemini SDK-compatible endpoints.
These allow direct use with the official google-generativeai Python SDK.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlmodel import Session, select
import json
import uuid
import time
import httpx

from app.core.database import get_session
from app.models.account import Account
from app.core.proxy.upstream import call_gemini_api, stream_gemini_api
from app.core.usage_logger import log_usage

router = APIRouter()


def get_mapped_model(requested_model: str) -> str:
    """Map incoming model name to an available model using database mappings."""
    # 1. Check Database for Custom Mappings
    try:
        from sqlmodel import select
        from app.core.database import get_session
        from app.models.mapping import ModelMapping
        
        session = next(get_session())
        mapping = session.exec(select(ModelMapping).where(ModelMapping.source_model == requested_model)).first()
        if mapping:
            print(f"[Gemini] Model mapping: {requested_model} -> {mapping.target_model}")
            return mapping.target_model
    except Exception as e:
        print(f"[Gemini] Error querying model mapping: {e}")
    
    # 2. Pass through as-is
    return requested_model



async def get_active_account(session: Session) -> Account:
    """Get an available account."""
    accounts = session.exec(select(Account)).all()
    if not accounts:
        raise HTTPException(status_code=503, detail="No accounts configured")
    return accounts[0]


@router.get("/models")
async def list_models(session: Session = Depends(get_session)):
    """
    List available Gemini models.
    Compatible with: google.generativeai.list_models()
    """
    # Static list of common models
    models = [
        {
            "name": "models/gemini-2.5-pro",
            "version": "001",
            "displayName": "Gemini 2.5 Pro",
            "description": "Most capable Gemini model for complex tasks",
            "inputTokenLimit": 1048576,
            "outputTokenLimit": 65536,
            "supportedGenerationMethods": ["generateContent", "countTokens"],
        },
        {
            "name": "models/gemini-2.5-flash",
            "version": "001",
            "displayName": "Gemini 2.5 Flash",
            "description": "Fast and efficient model for most tasks",
            "inputTokenLimit": 1048576,
            "outputTokenLimit": 65536,
            "supportedGenerationMethods": ["generateContent", "countTokens"],
        },
        {
            "name": "models/gemini-2.0-flash",
            "version": "001",
            "displayName": "Gemini 2.0 Flash",
            "description": "Previous generation flash model",
            "inputTokenLimit": 1048576,
            "outputTokenLimit": 8192,
            "supportedGenerationMethods": ["generateContent", "countTokens"],
        },
        {
            "name": "models/gemini-1.5-pro",
            "version": "001",
            "displayName": "Gemini 1.5 Pro",
            "description": "Balanced performance model",
            "inputTokenLimit": 2097152,
            "outputTokenLimit": 8192,
            "supportedGenerationMethods": ["generateContent", "countTokens"],
        },
    ]
    return {"models": models}


@router.get("/models/{model_name}")
async def get_model(model_name: str):
    """Get info about a specific model."""
    return {
        "name": f"models/{model_name}",
        "displayName": model_name,
        "supportedGenerationMethods": ["generateContent", "countTokens"]
    }


@router.post("/models/{model_action:path}")
async def generate_content(
    model_action: str,
    request: Request,
    session: Session = Depends(get_session)
):
    """
    Gemini generateContent / streamGenerateContent endpoint.
    
    Path format: /v1beta/models/{model}:generateContent
                 /v1beta/models/{model}:streamGenerateContent
    
    Compatible with: google.generativeai.GenerativeModel.generate_content()
    
    Note: Using {model_action:path} to capture the full path including colons.
    """
    # Parse model:method
    if ":" in model_action:
        model_name, method = model_action.rsplit(":", 1)
    else:
        model_name = model_action
        method = "generateContent"
    
    # Apply model mapping from database
    original_model = model_name
    model_name = get_mapped_model(model_name)
    if model_name != original_model:
        print(f"[Gemini] Applied mapping: {original_model} -> {model_name}")
    
    # Validate method
    if method not in ["generateContent", "streamGenerateContent"]:
        raise HTTPException(status_code=400, detail=f"Unsupported method: {method}")
    
    is_stream = method == "streamGenerateContent"
    
    # Get request body first
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    
    # Use token_manager with retry logic
    from app.core.token_manager import get_token_manager
    token_manager = get_token_manager()
    
    # Dynamic retry count based on number of accounts
    account_count = len(token_manager._tokens)
    max_retries = max(account_count, 5)
    
    last_error = None
    tried_accounts = set()
    
    for attempt in range(max_retries):
        start_time = time.time()
        try:
            force_rotate = attempt > 0
            access_token, project_id, email = await token_manager.get_token(
                quota_group="gemini",
                force_rotate=force_rotate
            )
            tried_accounts.add(email)
            
            # Build Gemini payload
            gemini_payload = {
                "project": project_id,
                "requestId": f"gemini-{uuid.uuid4()}",
                "request": body,
                "model": model_name,
                "userAgent": "antigravity-py",
                "requestType": "generate_content"
            }
            
            if is_stream:
                async def generate_stream():
                    try:
                        async for chunk in stream_gemini_api(gemini_payload, access_token):
                            if chunk.startswith("data:"):
                                data_str = chunk[5:].strip()
                                if data_str and data_str != "[DONE]":
                                    try:
                                        gemini_data = json.loads(data_str)
                                        if "response" in gemini_data:
                                            inner = gemini_data["response"]
                                            yield f"data: {json.dumps(inner)}\n\n"
                                        else:
                                            yield f"data: {data_str}\n\n"
                                    except json.JSONDecodeError:
                                        yield f"data: {data_str}\n\n"
                        yield "data: [DONE]\n\n"
                    except Exception as e:
                        error_chunk = {"error": {"message": str(e)}}
                        yield f"data: {json.dumps(error_chunk)}\n\n"
                
                response_time = int((time.time() - start_time) * 1000)
                log_usage("gemini", model_name, email, True, 200, response_time)
                return StreamingResponse(
                    generate_stream(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
                )
            else:
                gemini_response = await call_gemini_api(gemini_payload, access_token, stream=False)
                response_time = int((time.time() - start_time) * 1000)
                log_usage("gemini", model_name, email, True, 200, response_time)
                if "response" in gemini_response:
                    return JSONResponse(content=gemini_response["response"])
                return JSONResponse(content=gemini_response)
                
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e))
            
        except Exception as e:
            error_msg = str(e)
            last_error = e
            print(f"[Gemini] Attempt {attempt + 1}/{max_retries} FAILED ({email}): {error_msg[:100]}")
            
            # Retry on various errors
            if any(x in error_msg for x in ["429", "403", "500", "502", "503", "504"]):
                continue
            if any(x in error_msg.lower() for x in ["name resolution", "dns", "connect", "timeout", "connection"]):
                print(f"[Gemini] Network error detected, trying next account...")
                continue
            # Retry on any error
            continue
    
    print(f"[Gemini] All {max_retries} attempts failed. Tried: {tried_accounts}")
    raise HTTPException(status_code=429, detail=f"All accounts exhausted: {last_error}")


@router.post("/models/{model_name}/countTokens")
async def count_tokens(
    model_name: str,
    request: Request,
    session: Session = Depends(get_session)
):
    """
    Count tokens for content.
    Compatible with: google.generativeai.GenerativeModel.count_tokens()
    """
    try:
        body = await request.json()
        # Simple estimation: ~4 chars per token
        content_str = json.dumps(body)
        estimated_tokens = len(content_str) // 4
        return {"totalTokens": estimated_tokens}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
