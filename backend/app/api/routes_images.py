"""
Image Generation API Routes (OpenAI Compatible)

Uses v1internal generateContent with gemini-3-pro-image model.
Port of Rust implementation logic.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel, Field
import time
import base64

from app.core.token_manager import get_token_manager
from app.core.usage_logger import log_usage
from app.core.proxy.upstream import call_gemini_api

router = APIRouter()


# --- Request/Response Models ---

class ImageGenerationRequest(BaseModel):
    """Request model for image generation (OpenAI compatible)."""
    prompt: str = Field(..., description="A text description of the desired image(s).")
    model: Optional[str] = Field("gemini-3-pro-image", description="The model to use.")
    n: Optional[int] = Field(1, ge=1, le=4, description="Number of images to generate.")
    size: Optional[str] = Field("1024x1024", description="Size of the generated images.")
    response_format: Optional[str] = Field("b64_json", description="Format: url or b64_json.")


class Image(BaseModel):
    url: Optional[str] = None
    b64_json: Optional[str] = None
    revised_prompt: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    """Response model for image generation (OpenAI compatible)."""
    created: int
    data: List[Image]


# --- Helper Functions ---

def parse_aspect_ratio(size_or_model: str) -> str:
    """Parse aspect ratio from size string or model suffix."""
    # Check for explicit ratio suffixes (from Rust common_utils.rs)
    if "-16x9" in size_or_model:
        return "16:9"
    if "-9x16" in size_or_model:
        return "9:16"
    if "-4x3" in size_or_model:
        return "4:3"
    if "-3x4" in size_or_model:
        return "3:4"
    if "-1x1" in size_or_model:
        return "1:1"
    
    # Parse from size string (e.g., "1024x1024")
    if "x" in size_or_model:
        parts = size_or_model.lower().split("x")
        if len(parts) == 2:
            try:
                w, h = int(parts[0]), int(parts[1])
                if w == h:
                    return "1:1"
                elif w > h:
                    return "16:9" if w / h > 1.5 else "4:3"
                else:
                    return "9:16" if h / w > 1.5 else "3:4"
            except ValueError:
                pass
    
    return "1:1"


# --- API Endpoint ---

@router.post("/generations", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest):
    """
    Generate images using Gemini gemini-3-pro-image model.
    
    Uses v1internal:generateContent endpoint (same as chat).
    """
    
    # 1. Get token from pool
    token_manager = get_token_manager()
    try:
        access_token, project_id, email = await token_manager.get_token(quota_group="image_gen")
    except ValueError:
        raise HTTPException(status_code=503, detail="No active accounts available")

    # 2. Determine aspect ratio
    aspect_ratio = parse_aspect_ratio(request.size or "1024x1024")
    
    # 3. Build Gemini request body
    # Based on Rust wrapper.rs - wrap_request function
    # Key: imageConfig goes inside generationConfig, not as separate responseModalities
    import uuid
    
    inner_request = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": request.prompt}]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 64000,
            "imageConfig": {
                "aspectRatio": aspect_ratio
            }
        }
        # No tools, no systemInstruction for image generation
    }
    
    gemini_body = {
        "project": project_id,
        "requestId": f"agent-{uuid.uuid4()}",
        "request": inner_request,
        "model": "gemini-3-pro-image",
        "userAgent": "antigravity",
        "requestType": "image_gen"
    }
    
    # 4. Call upstream API with retry logic
    # Use number of accounts as max retries to ensure we try all accounts
    account_count = len(token_manager._tokens)
    max_retries = max(account_count, 5)  # At least 5 retries
    last_error = None
    tried_accounts = set()
    
    for attempt in range(max_retries):
        try:
            # If this is a retry, get a new token
            if attempt > 0:
                print(f"[ImageGen] Retry attempt {attempt + 1}/{max_retries}, switching account...")
                # Force rotate to get a different account
                access_token, project_id, email = await token_manager.get_token(quota_group="image_gen", force_rotate=True)
                # Update project_id in request body
                gemini_body["project"] = project_id
            
            # Log which account we're using
            print(f"[ImageGen] Attempt {attempt + 1}: Using account {email} (project: {project_id})")
            tried_accounts.add(email)
            
            response = await call_gemini_api(gemini_body, access_token, stream=False)
            print(f"[ImageGen] Success with account {email}")
            break # Success!
            
        except Exception as e:
            error_msg = str(e)
            last_error = e
            print(f"[ImageGen] Attempt {attempt + 1} FAILED ({email}): {error_msg[:150]}")
            
            # Retry on these errors (account-specific or transient):
            # - 429: Rate limit
            # - 403: Permission denied / bad project
            # - DNS/Network errors: Try different account (might have different network path)
            # - Connection errors: Transient network issues
            if "429" in error_msg or "403" in error_msg:
                continue
            elif "name resolution" in error_msg.lower() or "dns" in error_msg.lower():
                # DNS error - retry with different account
                print(f"[ImageGen] DNS error detected, trying next account...")
                continue
            elif "connect" in error_msg.lower() or "timeout" in error_msg.lower():
                # Connection/timeout error - retry
                print(f"[ImageGen] Network error detected, trying next account...")
                continue
            elif "500" in error_msg or "502" in error_msg or "503" in error_msg or "504" in error_msg:
                # Server errors - retry
                print(f"[ImageGen] Server error detected, trying next account...")
                continue
            else:
                # Unknown error - still retry but log warning
                print(f"[ImageGen] Unknown error, will retry: {error_msg[:100]}")
                continue
    else:
        # Loop finished without breaking = all retries failed
        error_msg = str(last_error)
        print(f"[ImageGen] All {max_retries} attempts failed. Tried accounts: {tried_accounts}")
        if "429" in error_msg:
            raise HTTPException(status_code=429, detail=f"Rate limited after {max_retries} attempts: {error_msg}")
        elif "403" in error_msg:
            raise HTTPException(status_code=403, detail=f"Permission denied after {max_retries} attempts: {error_msg}")
        else:
            raise HTTPException(status_code=502, detail=f"Upstream error: {error_msg}")

    # 5. Transform response to OpenAI format
    # Gemini response structure for image generation:
    # {
    #   "candidates": [
    #     {
    #       "content": {
    #         "parts": [
    #           { "inlineData": { "mimeType": "image/png", "data": "base64..." } }
    #         ]
    #       }
    #     }
    #   ]
    # }
    
    images = []
    candidates = response.get("candidates", [])
    
    for candidate in candidates:
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        
        for part in parts:
            inline_data = part.get("inlineData", {})
            b64_data = inline_data.get("data")
            
            if b64_data:
                if request.response_format == "url":
                    # Return as data URI
                    mime_type = inline_data.get("mimeType", "image/png")
                    images.append(Image(url=f"data:{mime_type};base64,{b64_data}"))
                else:
                    # Return as b64_json
                    images.append(Image(b64_json=b64_data))

    # Log successful image generation
    log_usage("image_gen", "gemini-3-pro-image", email, True, 200, int(time.time() * 1000 - time.time() * 1000))
    
    return ImageGenerationResponse(
        created=int(time.time()),
        data=images
    )
