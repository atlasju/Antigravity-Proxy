"""
OpenAI Protocol API Routes

Exposes OpenAI-compatible endpoints that proxy to Google Gemini.
Uses TokenManager for account rotation and 429 retry.
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
import json
import time
import httpx

from app.core.token_manager import get_token_manager
from app.core.usage_logger import log_usage
from app.core.proxy import (
    OpenAIRequest,
    transform_openai_to_gemini,
    transform_gemini_to_openai,
    call_gemini_api,
    stream_gemini_api,
)

router = APIRouter()

# Model mapping - only user-specified models
MODEL_MAPPING = {
    # User's preferred models
    "claude-opus-4-5-thinking": "claude-opus-4-5-thinking",
    "claude-sonnet-4-5-thinking": "claude-sonnet-4-5-thinking",
    "gemini-3-flash": "gemini-3-flash",
    "gemini-3-pro-high": "gemini-3-pro-high",
    "gemini-3-pro-low": "gemini-3-pro-low",
    "gpt-oss-120b-medium": "gpt-oss-120b-medium",
    # Legacy OpenAI model names (map to Gemini)
    "gpt-4": "gemini-3-pro-high",
    "gpt-4-turbo": "gemini-3-pro-high",
    "gpt-4o": "gemini-3-flash",
    "gpt-3.5-turbo": "gemini-3-flash",
}

MAX_RETRY_ATTEMPTS = 3


def get_mapped_model(requested_model: str) -> str:
    """Map incoming model name to an available model."""
    # 1. Check Database for Custom Mappings
    try:
        from sqlmodel import Session, select
        from app.core.database import engine
        from app.models.mapping import ModelMapping
        
        with Session(engine) as session:
            mapping = session.exec(select(ModelMapping).where(ModelMapping.source_model == requested_model)).first()
            if mapping:
                return mapping.target_model
    except Exception as e:
        print(f"Error querying model mapping: {e}")

    # 2. Check Hardcoded Defaults
    if requested_model in MODEL_MAPPING:
        return MODEL_MAPPING[requested_model]
        
    # 3. Pass through if model name looks valid
    if any(x in requested_model.lower() for x in ["gemini", "claude", "gpt"]):
        return requested_model
        
    # 4. Fallback default
    return "gemini-3-flash"


@router.post("/chat/completions")
async def chat_completions(request: Request):
    """
    OpenAI-compatible /v1/chat/completions endpoint.
    
    Features:
    - Account rotation via TokenManager
    - Auto 429 retry with account switching
    - Auto token refresh
    """
    try:
        body = await request.json()
        openai_request = OpenAIRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request format: {e}")
    
    token_manager = get_token_manager()
    mapped_model = get_mapped_model(openai_request.model)
    
    # Dynamic retry count based on number of accounts
    account_count = len(token_manager._tokens)
    max_retries = max(account_count, 5)  # At least 5 retries
    
    # Retry loop for errors
    last_error = None
    tried_accounts = set()
    
    for attempt in range(max_retries):
        start_time = time.time()
        try:
            # Get token from manager (handles rotation, refresh, etc.)
            force_rotate = attempt > 0  # Force rotation after first attempt
            access_token, project_id, email = await token_manager.get_token(
                quota_group="gemini",
                force_rotate=force_rotate
            )
            tried_accounts.add(email)
            
            # Transform request
            gemini_payload = transform_openai_to_gemini(openai_request, project_id, mapped_model)
            
            if openai_request.stream:
                # Log success for streaming (response time may not be accurate)
                response_time = int((time.time() - start_time) * 1000)
                log_usage("openai", mapped_model, email, True, 200, response_time)
                return await _handle_streaming(gemini_payload, access_token, mapped_model, email)
            else:
                result = await _handle_non_streaming(gemini_payload, access_token, mapped_model)
                response_time = int((time.time() - start_time) * 1000)
                log_usage("openai", mapped_model, email, True, 200, response_time)
                return result
                
        except httpx.HTTPStatusError as e:
            error_msg = str(e)
            last_error = e
            status = e.response.status_code
            print(f"[OpenAI] Attempt {attempt + 1}/{max_retries} FAILED ({email}): {status} - {error_msg[:100]}")
            
            # Retry on 429, 403, 500, 502, 503, 504
            if status in [429, 403, 500, 502, 503, 504]:
                continue
            raise HTTPException(status_code=status, detail=f"Upstream error: {e}")
            
        except ValueError as e:
            # No accounts available
            raise HTTPException(status_code=503, detail=str(e))
            
        except Exception as e:
            error_msg = str(e)
            last_error = e
            print(f"[OpenAI] Attempt {attempt + 1}/{max_retries} FAILED ({email}): {error_msg[:100]}")
            
            # Retry on network/DNS/timeout errors
            if any(x in error_msg.lower() for x in ["name resolution", "dns", "connect", "timeout", "connection"]):
                print(f"[OpenAI] Network error detected, trying next account...")
                continue
            # Retry on any other error too
            continue
    
    # All retries exhausted
    print(f"[OpenAI] All {max_retries} attempts failed. Tried: {tried_accounts}")
    log_usage("openai", mapped_model, email, False, 429, 0, "429")
    raise HTTPException(status_code=429, detail=f"All accounts exhausted: {last_error}")


async def _handle_streaming(gemini_payload: dict, access_token: str, model: str, email: str):
    """Handle streaming response."""
    async def generate_stream():
        try:
            async for chunk in stream_gemini_api(gemini_payload, access_token):
                if chunk.startswith("data:"):
                    data_str = chunk[5:].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            gemini_data = json.loads(data_str)
                            openai_chunk = _convert_stream_chunk(gemini_data, model)
                            yield f"data: {json.dumps(openai_chunk)}\n\n"
                        except json.JSONDecodeError:
                            pass
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_chunk = {"error": {"message": str(e), "type": "proxy_error"}}
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


async def _handle_non_streaming(gemini_payload: dict, access_token: str, model: str):
    """Handle non-streaming response."""
    gemini_response = await call_gemini_api(gemini_payload, access_token, stream=False)
    openai_response = transform_gemini_to_openai(gemini_response, model)
    return JSONResponse(content=openai_response.model_dump())


def _convert_stream_chunk(gemini_data: dict, model: str) -> dict:
    """Convert a Gemini streaming chunk to OpenAI delta format."""
    candidates = gemini_data.get("candidates", [])
    delta_content = ""
    
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if "text" in part:
                delta_content += part["text"]
    
    return {
        "id": f"chatcmpl-stream-{int(time.time())}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"content": delta_content} if delta_content else {},
            "finish_reason": None
        }]
    }


@router.get("/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
    models = [
        # User's preferred models
        {"id": "claude-opus-4-5-thinking", "object": "model", "owned_by": "antigravity"},
        {"id": "claude-sonnet-4-5-thinking", "object": "model", "owned_by": "antigravity"},
        {"id": "gemini-3-flash", "object": "model", "owned_by": "antigravity"},
        {"id": "gemini-3-pro-high", "object": "model", "owned_by": "antigravity"},
        {"id": "gemini-3-pro-low", "object": "model", "owned_by": "antigravity"},
        {"id": "gpt-oss-120b-medium", "object": "model", "owned_by": "antigravity"},
    ]
    return {"object": "list", "data": models}

