"""
OpenAI to Gemini Request Mapper

This module transforms OpenAI API request format into Google Gemini API format.
This is the core of the reverse proxy functionality.
"""
import uuid
from typing import Any, Dict, List, Optional
from .openai_models import OpenAIRequest, OpenAIMessage

def transform_openai_to_gemini(request: OpenAIRequest, project_id: str, mapped_model: str) -> Dict[str, Any]:
    """
    Transform an OpenAI ChatCompletion request into a Gemini GenerateContent request.
    
    Args:
        request: The incoming OpenAI format request.
        project_id: The Google Cloud project ID for the account.
        mapped_model: The target Gemini model name (e.g., "gemini-2.5-flash").
    
    Returns:
        A dictionary representing the Gemini API request payload.
    """
    
    # 1. Extract System Instructions
    system_instructions: List[str] = []
    for msg in request.messages:
        if msg.role == "system" and msg.content:
            if isinstance(msg.content, str):
                system_instructions.append(msg.content)
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        system_instructions.append(block.get("text", ""))
    
    # 2. Build Gemini `contents` (filter out system messages)
    contents: List[Dict[str, Any]] = []
    for msg in request.messages:
        if msg.role == "system":
            continue
        
        role = "model" if msg.role == "assistant" else ("user" if msg.role in ["user", "tool", "function"] else msg.role)
        parts: List[Dict[str, Any]] = []
        
        # Handle content (text or multimodal)
        if msg.content:
            if isinstance(msg.content, str):
                if msg.content:
                    parts.append({"text": msg.content})
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            parts.append({"text": block.get("text", "")})
                        elif block.get("type") == "image_url":
                            image_url_data = block.get("image_url", {})
                            url = image_url_data.get("url", "")
                            if url.startswith("data:"):
                                # Base64 encoded image
                                try:
                                    meta, data = url.split(",", 1)
                                    mime_type = meta.split(":")[1].split(";")[0]
                                    parts.append({"inlineData": {"mimeType": mime_type, "data": data}})
                                except (ValueError, IndexError):
                                    pass # Skip malformed data URLs
                            elif url.startswith("http"):
                                parts.append({"fileData": {"fileUri": url, "mimeType": "image/jpeg"}})
        
        # Handle tool calls (from assistant)
        if msg.tool_calls:
            for tc in msg.tool_calls:
                import json
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                parts.append({
                    "functionCall": {
                        "name": tc.function.name,
                        "args": args
                    }
                })
        
        # Handle tool response (from user/tool role)
        if msg.role == "tool" or msg.role == "function":
            tool_name = msg.name or "unknown"
            content_val = msg.content if isinstance(msg.content, str) else ""
            parts.append({
                "functionResponse": {
                    "name": tool_name,
                    "id": msg.tool_call_id or "unknown",
                    "response": {"result": content_val}
                }
            })
        
        if parts:
            contents.append({"role": role, "parts": parts})
    
    # 3. Build Generation Config
    gen_config: Dict[str, Any] = {
        "maxOutputTokens": request.max_tokens or 64000,
        "temperature": request.temperature or 1.0,
        "topP": request.top_p or 1.0,
    }
    
    if request.stop:
        if isinstance(request.stop, str):
            gen_config["stopSequences"] = [request.stop]
        elif isinstance(request.stop, list):
            gen_config["stopSequences"] = request.stop
    
    if request.response_format and request.response_format.type == "json_object":
        gen_config["responseMimeType"] = "application/json"
    
    # 4. Build Inner Request
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
    
    # 5. Handle Tools
    if request.tools:
        function_declarations = []
        for tool in request.tools:
            func = tool.get("function", tool)
            # Basic cleaning
            func_copy = {k: v for k, v in func.items() if k not in ["type", "strict", "additionalProperties"]}
            if "parameters" in func_copy:
                _clean_json_schema(func_copy["parameters"])
            function_declarations.append(func_copy)
        
        if function_declarations:
            inner_request["tools"] = [{"functionDeclarations": function_declarations}]
    
    # 6. Add System Instruction
    if system_instructions:
        inner_request["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_instructions)}]}
    
    # 7. Wrap in final request structure
    return {
        "project": project_id,
        "requestId": f"openai-{uuid.uuid4()}",
        "request": inner_request,
        "model": mapped_model,
        "userAgent": "antigravity-py",
        "requestType": "generate_content"
    }


def _clean_json_schema(schema: Dict[str, Any]):
    """
    Recursively clean a JSON Schema to be compatible with Gemini's requirements.
    Gemini only supports a subset of JSON Schema keywords.
    """
    allowed_keys = {"type", "description", "properties", "required", "items", "enum", "format", "nullable"}
    keys_to_remove = [k for k in schema.keys() if k not in allowed_keys]
    for k in keys_to_remove:
        del schema[k]
    
    # Convert type to uppercase (Gemini convention)
    if "type" in schema and isinstance(schema["type"], str):
        schema["type"] = schema["type"].upper()
    
    # Recurse into properties
    if "properties" in schema and isinstance(schema["properties"], dict):
        for prop_schema in schema["properties"].values():
            if isinstance(prop_schema, dict):
                _clean_json_schema(prop_schema)
    
    # Recurse into items
    if "items" in schema and isinstance(schema["items"], dict):
        _clean_json_schema(schema["items"])
