from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

# --- Chat Completion ---
class ChatMessage(BaseModel):
    role: str  # 'system', 'user', 'assistant', 'tool', etc.
    content: Optional[str] = None
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None  # For function calling
    tool_call_id: Optional[str] = None  # For tool use
    tool_calls: Optional[List[Dict[str, Any]]] = None  # For tool use

class FunctionCall(BaseModel):
    name: str
    arguments: str

class ToolCall(BaseModel):
    id: str
    type: str
    function: FunctionCall

class FunctionDef(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]

class ToolDef(BaseModel):
    type: str  # 'function' (future: other types)
    function: FunctionDef

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    functions: Optional[List[FunctionDef]] = None
    tools: Optional[List[ToolDef]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    function_call: Optional[Union[str, Dict[str, Any]]] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    # MCP passthrough fields
    mcp: Optional[Dict[str, Any]] = None
    # Accept extra fields for forward compatibility
    class Config:
        extra = "allow"

class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[Usage] = None

# --- Completion (legacy) ---
class CompletionRequest(BaseModel):
    model: str
    prompt: Union[str, List[str]]
    suffix: Optional[str] = None
    max_tokens: Optional[int] = 16
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    logprobs: Optional[int] = None
    echo: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    best_of: Optional[int] = None
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    # MCP passthrough fields
    mcp: Optional[Dict[str, Any]] = None
    class Config:
        extra = "allow"

class CompletionChoice(BaseModel):
    text: str
    index: int
    logprobs: Optional[Any] = None
    finish_reason: Optional[str] = None

class CompletionResponse(BaseModel):
    id: str
    object: str = "text_completion"
    created: int
    model: str
    choices: List[CompletionChoice]
    usage: Optional[Usage] = None

# --- Error Model ---
class OpenAIErrorDetails(BaseModel):
    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None

class OpenAIErrorResponse(BaseModel):
    error: OpenAIErrorDetails
