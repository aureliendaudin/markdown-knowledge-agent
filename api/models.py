from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    modules: Optional[Dict[str, bool]] = None  # Override module settings per request

class ChatResponse(BaseModel):
    response: str
    context_used: Optional[List[Dict[str, Any]]] = None
    processing_time: float
    logs: List[str] = []
    full_prompt: Optional[List[Dict[str, Any]]] = None

class MemoryState(BaseModel):
    history: List[Dict[str, str]]
    concepts: Dict[str, Any]
    user_context: Dict[str, Any]

class HealthCheck(BaseModel):
    status: str
    modules_active: List[str]
