"""
OpenAI Protocol Models

These Pydantic models define the structure of OpenAI API requests and responses.
They are used for validation and serialization.
"""
from typing import Optional, List, Union, Any, Dict
from pydantic import BaseModel, Field

class OpenAIImageUrl(BaseModel):
    url: str
    detail: Optional[str] = None

class OpenAIContentBlockText(BaseModel):
    type: str = "text"
    text: str

class OpenAIContentBlockImage(BaseModel):
    type: str = "image_url"
    image_url: OpenAIImageUrl

# Union for content blocks
OpenAIContentBlock = Union[OpenAIContentBlockText, OpenAIContentBlockImage]

class OpenAIFunctionCall(BaseModel):
    name: str
    arguments: str

class OpenAIToolCall(BaseModel):
    id: str
    type: str = "function"
    function: OpenAIFunctionCall

class OpenAIMessage(BaseModel):
    role: str
    content: Optional[Union[str, List[Dict[str, Any]]]] = None
    tool_calls: Optional[List[OpenAIToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

class OpenAIResponseFormat(BaseModel):
    type: str

class OpenAIRequest(BaseModel):
    model: str
    messages: List[OpenAIMessage]
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stop: Optional[Union[str, List[str]]] = None
    response_format: Optional[OpenAIResponseFormat] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None

# --- OpenAI Response Models ---
class OpenAIChoiceMessage(BaseModel):
    role: str = "assistant"
    content: Optional[str] = None
    tool_calls: Optional[List[OpenAIToolCall]] = None

class OpenAIChoice(BaseModel):
    index: int = 0
    message: OpenAIChoiceMessage
    finish_reason: Optional[str] = "stop"

class OpenAIUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class OpenAIChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OpenAIChoice]
    usage: Optional[OpenAIUsage] = None
