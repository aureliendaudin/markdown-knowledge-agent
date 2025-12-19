from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    context_used: Optional[List[Dict[str, Any]]] = None
    processing_time: float
    logs: List[str] = []

class HealthCheck(BaseModel):
    status: str
    modules_active: List[str]
