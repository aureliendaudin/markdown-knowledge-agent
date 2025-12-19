import time
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from utils import setup_logging
from core import ObsidianAgent
from .models import ChatRequest, ChatResponse, HealthCheck, MemoryState

# Setup logging
setup_logging(settings.logging.level)
logger = logging.getLogger("api")

# Global agent instance
agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize agent on startup."""
    global agent
    logger.info("Initializing Obsidian Agent...")
    try:
        agent = ObsidianAgent()
        logger.info("Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise e
    yield
    # Cleanup if needed
    logger.info("Shutting down...")

app = FastAPI(
    title="Markdown Knowledge Agent API",
    description="API for the Obsidian Knowledge Agent",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for the frontend
app.mount("/ui", StaticFiles(directory="api/static", html=True), name="static")

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    active_modules = [name for name, m in agent.modules.items() if m.enabled]
    return HealthCheck(status="healthy", modules_active=active_modules)

@app.get("/memory", response_model=MemoryState)
async def get_memory():
    """Get current memory state."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return agent.get_memory_state()

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the agent."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    start_time = time.time()
    
    try:
        result = agent.ask(request.message, active_modules=request.modules)
        
        # Handle both string (legacy) and dict return types for safety
        if isinstance(result, dict):
            response_text = result["answer"]
            logs = result.get("logs", [])
            full_prompt = result.get("full_prompt", [])
            context = result.get("memory_context", [])
        else:
            response_text = result
            logs = []
            full_prompt = []
            context = []
            
        processing_time = time.time() - start_time
        
        return ChatResponse(
            response=response_text,
            context_used=context,
            processing_time=processing_time,
            logs=logs,
            full_prompt=full_prompt
        )
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
