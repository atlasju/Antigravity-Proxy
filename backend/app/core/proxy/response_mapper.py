"""
Gemini to OpenAI Response Mapper

Transforms Gemini API responses back into OpenAI API format.
"""
import time
import uuid
from typing import Any, Dict, Optional
from .openai_models import (
    OpenAIChatCompletionResponse,
    OpenAIChoice,
    OpenAIChoiceMessage,
    OpenAIUsage,
    OpenAIToolCall,
    OpenAIFunctionCall,
)


def transform_gemini_to_openai(gemini_response: Dict[str, Any], model: str) -> OpenAIChatCompletionResponse:
    """
    Transform a Gemini GenerateContent response into OpenAI ChatCompletion format.
    
    Args:
        gemini_response: The response from Gemini API.
        model: The model name to include in the response.
    
    Returns:
        An OpenAI-formatted ChatCompletion response.
    """
    candidates = gemini_response.get("candidates", [])
    
    content: Optional[str] = None
    tool_calls: Optional[list] = None
    finish_reason = "stop"
    
    if candidates:
        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        
        text_parts = []
        function_calls = []
        
        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                function_calls.append(OpenAIToolCall(
                    id=f"call_{uuid.uuid4().hex[:8]}",
                    type="function",
                    function=OpenAIFunctionCall(
                        name=fc.get("name", ""),
                        arguments=_dict_to_json_string(fc.get("args", {}))
                    )
                ))
        
        if text_parts:
            content = "".join(text_parts)
        if function_calls:
            tool_calls = function_calls
            finish_reason = "tool_calls"
        
        # Map Gemini finish reason to OpenAI
        gemini_finish = candidate.get("finishReason", "")
        if gemini_finish == "STOP":
            finish_reason = "stop"
        elif gemini_finish == "MAX_TOKENS":
            finish_reason = "length"
    
    # Extract usage metadata
    usage_meta = gemini_response.get("usageMetadata", {})
    usage = OpenAIUsage(
        prompt_tokens=usage_meta.get("promptTokenCount", 0),
        completion_tokens=usage_meta.get("candidatesTokenCount", 0),
        total_tokens=usage_meta.get("totalTokenCount", 0)
    )
    
    return OpenAIChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
        object="chat.completion",
        created=int(time.time()),
        model=model,
        choices=[
            OpenAIChoice(
                index=0,
                message=OpenAIChoiceMessage(
                    role="assistant",
                    content=content,
                    tool_calls=tool_calls
                ),
                finish_reason=finish_reason
            )
        ],
        usage=usage
    )


def _dict_to_json_string(d: Dict[str, Any]) -> str:
    import json
    return json.dumps(d)
