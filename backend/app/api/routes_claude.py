"""
Claude/Anthropic Protocol API Routes

Exposes Anthropic-compatible endpoints that proxy to Google Gemini.
Uses TokenManager for account rotation and 429 retry.
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
import json
import time
import httpx

from app.core.token_manager import get_token_manager
from app.core.usage_logger import log_usage
from app.core.proxy.claude_models import ClaudeRequest
from app.core.proxy.claude_mapper import transform_claude_to_gemini
from app.core.proxy.claude_response_mapper import transform_gemini_to_claude
from app.core.proxy.upstream import call_gemini_api, stream_gemini_api

router = APIRouter()

# Model mapping for Claude protocol requests
CLAUDE_MODEL_MAPPING = {
    # User's preferred models (pass through)
    "claude-opus-4-5-thinking": "claude-opus-4-5-thinking",
    "claude-sonnet-4-5-thinking": "claude-sonnet-4-5-thinking",
    # Legacy Claude model names
    "claude-3-5-sonnet-20241022": "claude-sonnet-4-5-thinking",
    "claude-3-5-sonnet": "claude-sonnet-4-5-thinking",
    "claude-sonnet-4-20250514": "claude-sonnet-4-5-thinking",
    "claude-3-opus": "claude-opus-4-5-thinking",
    "claude-3-haiku": "gemini-3-flash",
    "claude-3-5-haiku": "gemini-3-flash",
}

MAX_RETRY_ATTEMPTS = 3


def get_mapped_model(requested_model: str) -> str:
    """Map Claude model name to available model."""
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

    # 2. Check Defaults
    if requested_model in CLAUDE_MODEL_MAPPING:
        return CLAUDE_MODEL_MAPPING[requested_model]
    
    # 3. Pass through
    if any(x in requested_model.lower() for x in ["gemini", "claude", "gpt"]):
        return requested_model
    
    # 4. Fallback
    return "gemini-3-flash"


@router.post("/messages")
async def messages(request: Request):
    """
    Anthropic-compatible /v1/messages endpoint.
    
    Features:
    - Account rotation via TokenManager
    - Auto 429 retry with account switching
    """
    try:
        body = await request.json()
        claude_request = ClaudeRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request format: {e}")
    
    token_manager = get_token_manager()
    mapped_model = get_mapped_model(claude_request.model)
    
    # Dynamic retry count based on number of accounts
    account_count = len(token_manager._tokens)
    max_retries = max(account_count, 5)  # At least 5 retries
    
    # Retry loop for errors
    last_error = None
    tried_accounts = set()
    
    for attempt in range(max_retries):
        start_time = time.time()
        try:
            force_rotate = attempt > 0
            access_token, project_id, email = await token_manager.get_token(
                quota_group="claude",
                force_rotate=force_rotate
            )
            tried_accounts.add(email)
            
            gemini_payload = transform_claude_to_gemini(claude_request, project_id, mapped_model)
            
            if claude_request.stream:
                response_time = int((time.time() - start_time) * 1000)
                log_usage("claude", mapped_model, email, True, 200, response_time)
                return await _handle_streaming(gemini_payload, access_token, claude_request.model)
            else:
                result = await _handle_non_streaming(gemini_payload, access_token, claude_request.model)
                response_time = int((time.time() - start_time) * 1000)
                log_usage("claude", mapped_model, email, True, 200, response_time)
                return result
                
        except httpx.HTTPStatusError as e:
            error_msg = str(e)
            last_error = e
            status = e.response.status_code
            print(f"[Claude] Attempt {attempt + 1}/{max_retries} FAILED ({email}): {status} - {error_msg[:100]}")
            
            # Retry on 429, 403, 500, 502, 503, 504
            if status in [429, 403, 500, 502, 503, 504]:
                continue
            raise HTTPException(status_code=status, detail=f"Upstream error: {e}")
            
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e))
            
        except Exception as e:
            error_msg = str(e)
            last_error = e
            print(f"[Claude] Attempt {attempt + 1}/{max_retries} FAILED ({email}): {error_msg[:100]}")
            
            # Retry on network/DNS/timeout errors
            if any(x in error_msg.lower() for x in ["name resolution", "dns", "connect", "timeout", "connection"]):
                print(f"[Claude] Network error detected, trying next account...")
                continue
            # Retry on any other error too
            continue
    
    print(f"[Claude] All {max_retries} attempts failed. Tried: {tried_accounts}")
    raise HTTPException(status_code=429, detail=f"All accounts exhausted: {last_error}")


async def _handle_streaming(gemini_payload: dict, access_token: str, model: str):
    """Handle Claude streaming response."""
    async def generate_stream():
        message_id = f"msg_{int(time.time())}"
        
        # 1. message_start event
        yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': message_id, 'type': 'message', 'role': 'assistant', 'model': model, 'content': [], 'stop_reason': None, 'usage': {'input_tokens': 0, 'output_tokens': 0}}})}\n\n"
        
        # 2. content_block_start
        yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"
        
        try:
            async for chunk in stream_gemini_api(gemini_payload, access_token):
                if chunk.startswith("data:"):
                    data_str = chunk[5:].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            gemini_data = json.loads(data_str)
                            delta_text = _extract_text_delta(gemini_data)
                            if delta_text:
                                delta_event = {
                                    "type": "content_block_delta",
                                    "index": 0,
                                    "delta": {"type": "text_delta", "text": delta_text}
                                }
                                yield f"event: content_block_delta\ndata: {json.dumps(delta_event)}\n\n"
                        except json.JSONDecodeError:
                            pass
            
            yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
            yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn'}, 'usage': {'output_tokens': 0}})}\n\n"
            yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"
            
        except Exception as e:
            error_event = {"type": "error", "error": {"type": "proxy_error", "message": str(e)}}
            yield f"event: error\ndata: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


async def _handle_non_streaming(gemini_payload: dict, access_token: str, model: str):
    """Handle Claude non-streaming response."""
    gemini_response = await call_gemini_api(gemini_payload, access_token, stream=False)
    claude_response = transform_gemini_to_claude(gemini_response, model)
    return JSONResponse(content=claude_response.model_dump())


def _extract_text_delta(gemini_data: dict) -> str:
    """Extract text content from Gemini streaming chunk."""
    candidates = gemini_data.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if "text" in part and not part.get("thought"):
                return part["text"]
    return ""


@router.post("/messages/count_tokens")
async def count_tokens(request: Request):
    """Token counting endpoint (simplified)."""
    try:
        body = await request.json()
        total_chars = len(json.dumps(body))
        estimated_tokens = total_chars // 4
        return {"input_tokens": estimated_tokens}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

