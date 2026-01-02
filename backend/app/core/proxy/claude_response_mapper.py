"""
Gemini to Claude Response Mapper

Transforms Gemini responses back into Claude/Anthropic format.
"""
import time
import uuid
from typing import Any, Dict, List, Optional
from .claude_models import (
    ClaudeMessagesResponse,
    ClaudeResponseContentBlock,
    ClaudeUsage,
)


def transform_gemini_to_claude(gemini_response: Dict[str, Any], model: str) -> ClaudeMessagesResponse:
    """
    Transform a Gemini response into Claude /v1/messages format.
    """
    candidates = gemini_response.get("candidates", [])
    
    content_blocks: List[ClaudeResponseContentBlock] = []
    stop_reason = "end_turn"
    
    if candidates:
        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        
        for part in parts:
            if part.get("thought"):
                # Thinking block
                content_blocks.append(ClaudeResponseContentBlock(
                    type="thinking",
                    text=part.get("text", "")
                ))
            elif "text" in part:
                content_blocks.append(ClaudeResponseContentBlock(
                    type="text",
                    text=part["text"]
                ))
            elif "functionCall" in part:
                fc = part["functionCall"]
                content_blocks.append(ClaudeResponseContentBlock(
                    type="tool_use",
                    id=f"toolu_{uuid.uuid4().hex[:12]}",
                    name=fc.get("name", ""),
                    input=fc.get("args", {})
                ))
        
        # Map finish reason
        gemini_finish = candidate.get("finishReason", "")
        if gemini_finish == "STOP":
            stop_reason = "end_turn"
        elif gemini_finish == "MAX_TOKENS":
            stop_reason = "max_tokens"
        elif gemini_finish == "TOOL_USE":
            stop_reason = "tool_use"
    
    # Usage
    usage_meta = gemini_response.get("usageMetadata", {})
    usage = ClaudeUsage(
        input_tokens=usage_meta.get("promptTokenCount", 0),
        output_tokens=usage_meta.get("candidatesTokenCount", 0)
    )
    
    return ClaudeMessagesResponse(
        id=f"msg_{uuid.uuid4().hex[:12]}",
        type="message",
        role="assistant",
        model=model,
        content=[b.model_dump(exclude_none=True) for b in content_blocks],
        stop_reason=stop_reason,
        usage=usage
    )
