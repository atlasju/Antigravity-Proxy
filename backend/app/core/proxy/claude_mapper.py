"""
Claude to Gemini Request Mapper

Transforms Anthropic Claude API requests into Google Gemini format.
"""
import uuid
from typing import Any, Dict, List, Optional
from .claude_models import ClaudeRequest, ClaudeMessage

def transform_claude_to_gemini(request: ClaudeRequest, project_id: str, mapped_model: str) -> Dict[str, Any]:
    """
    Transform a Claude /v1/messages request into Gemini GenerateContent format.
    
    Args:
        request: The incoming Claude format request.
        project_id: Google Cloud project ID.
        mapped_model: Target Gemini model name.
    
    Returns:
        Gemini API request payload.
    """
    
    # 1. Extract System Prompt
    system_text = ""
    if request.system:
        if isinstance(request.system, str):
            system_text = request.system
        elif isinstance(request.system, list):
            # Array of system blocks
            parts = []
            for block in request.system:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
            system_text = "\n".join(parts)
    
    # 2. Convert Messages to Gemini contents
    contents: List[Dict[str, Any]] = []
    
    for msg in request.messages:
        role = "model" if msg.role == "assistant" else "user"
        parts: List[Dict[str, Any]] = []
        
        if isinstance(msg.content, str):
            if msg.content:
                parts.append({"text": msg.content})
        elif isinstance(msg.content, list):
            for block in msg.content:
                if isinstance(block, dict):
                    block_type = block.get("type", "")
                    
                    if block_type == "text":
                        text = block.get("text", "")
                        if text:
                            parts.append({"text": text})
                    
                    elif block_type == "thinking":
                        # Claude thinking block -> Gemini thought part
                        thinking_text = block.get("thinking", "")
                        if thinking_text:
                            parts.append({
                                "text": thinking_text,
                                "thought": True
                            })
                    
                    elif block_type == "image":
                        source = block.get("source", {})
                        if source.get("type") == "base64":
                            parts.append({
                                "inlineData": {
                                    "mimeType": source.get("media_type", "image/jpeg"),
                                    "data": source.get("data", "")
                                }
                            })
                    
                    elif block_type == "tool_use":
                        # Assistant's tool call
                        parts.append({
                            "functionCall": {
                                "name": block.get("name", ""),
                                "args": block.get("input", {})
                            }
                        })
                    
                    elif block_type == "tool_result":
                        # User's tool response
                        tool_content = block.get("content", "")
                        if isinstance(tool_content, str):
                            result_text = tool_content
                        else:
                            # Array of blocks
                            result_text = str(tool_content)
                        
                        parts.append({
                            "functionResponse": {
                                "name": "tool",  # Claude doesn't include name in result
                                "response": {"result": result_text}
                            }
                        })
        
        if parts:
            contents.append({"role": role, "parts": parts})
    
    # 3. Generation Config
    gen_config: Dict[str, Any] = {
        "maxOutputTokens": request.max_tokens or 64000,
        "temperature": request.temperature or 1.0,
    }
    
    if request.top_p:
        gen_config["topP"] = request.top_p
    if request.top_k:
        gen_config["topK"] = request.top_k
    
    # Handle thinking mode
    if request.thinking and request.thinking.type == "enabled":
        gen_config["thinkingConfig"] = {
            "thinkingBudget": request.thinking.budget_tokens or 10000
        }
    
    # 4. Build inner request
    inner_request: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": gen_config,
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "OFF"},
        ]
    }
    
    # 5. System instruction
    if system_text:
        inner_request["systemInstruction"] = {"parts": [{"text": system_text}]}
    
    # 6. Convert tools
    if request.tools:
        function_declarations = []
        inject_google_search = False
        
        for tool in request.tools:
            # Check for web search server tool
            if tool.type and tool.type.startswith("web_search"):
                inject_google_search = True
                continue
            if tool.name == "web_search":
                inject_google_search = True
                continue
            
            # Regular function tool
            func_decl = {
                "name": tool.name,
                "description": tool.description or "",
            }
            if tool.input_schema:
                func_decl["parameters"] = _clean_schema(tool.input_schema)
            function_declarations.append(func_decl)
        
        if function_declarations:
            inner_request["tools"] = [{"functionDeclarations": function_declarations}]
        
        if inject_google_search:
            if "tools" not in inner_request:
                inner_request["tools"] = []
            inner_request["tools"].append({"googleSearch": {}})
    
    return {
        "project": project_id,
        "requestId": f"claude-{uuid.uuid4()}",
        "request": inner_request,
        "model": mapped_model,
        "userAgent": "antigravity-py",
        "requestType": "generate_content"
    }


def _clean_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Clean JSON Schema for Gemini compatibility."""
    import copy
    result = copy.deepcopy(schema)
    
    allowed_keys = {"type", "description", "properties", "required", "items", "enum", "format", "nullable"}
    
    def clean(obj):
        if isinstance(obj, dict):
            to_remove = [k for k in obj if k not in allowed_keys]
            for k in to_remove:
                del obj[k]
            if "type" in obj and isinstance(obj["type"], str):
                obj["type"] = obj["type"].upper()
            for v in obj.values():
                clean(v)
        elif isinstance(obj, list):
            for item in obj:
                clean(item)
    
    clean(result)
    return result
