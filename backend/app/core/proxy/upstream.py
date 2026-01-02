"""
Upstream Client

Handles making requests to the Google Gemini API via cloudcode-pa.
"""
import httpx
from typing import Any, Dict, Optional, AsyncIterator
import json

# v1internal API endpoint (same as Antigravity desktop app)
V1_INTERNAL_BASE_URL = "https://cloudcode-pa.googleapis.com/v1internal"

async def call_gemini_api(
    payload: Dict[str, Any],
    access_token: str,
    stream: bool = False
) -> Dict[str, Any]:
    """
    Make a non-streaming request to the Gemini API via v1internal.
    
    Args:
        payload: The Gemini-formatted request payload with project, model, request fields.
        access_token: OAuth access token for authentication.
        stream: Whether to request streaming response.
    
    Returns:
        The JSON response from Gemini.
    """
    method = "streamGenerateContent" if stream else "generateContent"
    url = f"{V1_INTERNAL_BASE_URL}:{method}"
    if stream:
        url += "?alt=sse"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "antigravity/python/1.0",
        "Host": "cloudcode-pa.googleapis.com",
    }
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        # Unwrap v1internal response wrapper if present
        if "response" in result:
            return result["response"]
        return result


async def stream_gemini_api(
    payload: Dict[str, Any],
    access_token: str
) -> AsyncIterator[str]:
    """
    Make a streaming request to the Gemini API and yield SSE chunks.
    
    Args:
        payload: The Gemini-formatted request payload.
        access_token: OAuth access token.
    
    Yields:
        SSE formatted strings.
    """
    url = f"{V1_INTERNAL_BASE_URL}:streamGenerateContent?alt=sse"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "antigravity/python/1.0",
        "Host": "cloudcode-pa.googleapis.com",
    }
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    # Unwrap v1internal response wrapper if present
                    data_str = line[5:].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            data = json.loads(data_str)
                            if "response" in data:
                                yield f"data: {json.dumps(data['response'])}"
                            else:
                                yield line
                        except json.JSONDecodeError:
                            yield line
                    else:
                        yield line

