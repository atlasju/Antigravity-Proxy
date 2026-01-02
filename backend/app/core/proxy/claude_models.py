"""
Claude/Anthropic Protocol Models

Pydantic models for Anthropic Claude API format.
"""
from typing import Optional, List, Union, Any, Dict
from pydantic import BaseModel, Field

# --- Request Models ---

class ClaudeImageSource(BaseModel):
    type: str = "base64"
    media_type: str
    data: str

class ClaudeContentBlockText(BaseModel):
    type: str = "text"
    text: str

class ClaudeContentBlockImage(BaseModel):
    type: str = "image"
    source: ClaudeImageSource

class ClaudeContentBlockToolUse(BaseModel):
    type: str = "tool_use"
    id: str
    name: str
    input: Dict[str, Any]

class ClaudeContentBlockToolResult(BaseModel):
    type: str = "tool_result"
    tool_use_id: str
    content: Any  # Can be string or list of blocks
    is_error: Optional[bool] = None

class ClaudeContentBlockThinking(BaseModel):
    type: str = "thinking"
    thinking: str
    signature: Optional[str] = None

# Union type for content blocks
ClaudeContentBlock = Union[
    ClaudeContentBlockText,
    ClaudeContentBlockImage,
    ClaudeContentBlockToolUse,
    ClaudeContentBlockToolResult,
    ClaudeContentBlockThinking,
    Dict[str, Any]  # Fallback for unknown types
]

class ClaudeMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: Union[str, List[Dict[str, Any]]]

class ClaudeTool(BaseModel):
    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    type: Optional[str] = None  # For server tools like "web_search_20250305"

class ClaudeThinkingConfig(BaseModel):
    type: str = "enabled"
    budget_tokens: Optional[int] = None

class ClaudeRequest(BaseModel):
    model: str
    messages: List[ClaudeMessage]
    system: Optional[Union[str, List[Dict[str, Any]]]] = None
    tools: Optional[List[ClaudeTool]] = None
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    thinking: Optional[ClaudeThinkingConfig] = None

# --- Response Models ---

class ClaudeUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0

class ClaudeResponseContentBlock(BaseModel):
    type: str
    text: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    input: Optional[Dict[str, Any]] = None

class ClaudeMessagesResponse(BaseModel):
    id: str
    type: str = "message"
    role: str = "assistant"
    model: str
    content: List[ClaudeResponseContentBlock]
    stop_reason: Optional[str] = "end_turn"
    stop_sequence: Optional[str] = None
    usage: ClaudeUsage
