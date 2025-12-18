"""Core agent implementation."""
import logging
from typing import Any
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from config import settings
from tools import get_all_tools
from modules import RetrievalModule, PlannerExecutorModule, MemoryModule

logger = logging.getLogger(__name__)


class ObsidianAgent:
    """Main Obsidian Agent with modular architecture."""
    
    def __init__(self):
        """Initialize agent with configured modules."""
        self.model = self._create_model()
        self.tools = get_all_tools()
        self.modules = self._initialize_modules()
        self.agent = self._create_agent()
    
    def _create_model(self):
        """Create LLM model based on configuration."""
        if settings.model.provider == "ollama":
            logger.info(f"Using Ollama model: {settings.model.ollama.model}")
            return ChatOllama(
                model=settings.model.ollama.model,
                base_url=settings.model.ollama.base_url,
                temperature=settings.model.temperature,
                num_ctx=settings.model.num_ctx,
            )
        else:
            raise ValueError(f"Unknown model provider: {settings.model.provider}")
    
    def _initialize_modules(self) -> dict[str, Any]:
        """Initialize all enabled modules."""
        modules = {}
        
        if settings.modules.retrieval.enabled:
            modules["retrieval"] = RetrievalModule(
                config=settings.modules.retrieval.model_dump()
            )
        
        # Planning module (Planner-Executor pattern)
        if settings.modules.planning.enabled:
            modules["planning"] = PlannerExecutorModule(
                model=self.model,
                tools=self.tools,
                config=settings.modules.planning.model_dump()
            )
        # Memory module
        if settings.modules.memory.enabled:
            modules["memory"] = MemoryModule(
                config=settings.modules.memory.model_dump()
            )
        
        for name, module in modules.items():
            module.initialize()
            logger.info(f"Module '{name}' initialized")
        
        return modules
    
    def _create_agent(self):
        """Create LangChain agent."""
        self.system_prompt = self.modules["retrieval"].get_system_prompt()
        
        return create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=self.system_prompt
        )
    
    def ask(self, question: str, active_modules: dict[str, bool] | None = None) -> dict[str, Any]:
        """
        Ask a question to the agent.
        
        Args:
            question: The user's question
            active_modules: Optional dictionary to override module enabled state
                          e.g. {"memory": False, "retrieval": True}
        """
        logger.info(f"Question: {question}")
        logs = []
        
        # If planning module is enabled, use Planner-Executor pattern
        if "planning" in self.modules and self.modules["planning"].enabled:
            logger.info("Using Planner-Executor mode")
            state = {"question": question}
            state = self.modules["planning"].process(state)
            answer = state.get("answer", "No answer generated")
            logger.info(f"Answer generated ({len(answer)} chars)")
            return answer
        
        # Otherwise, use standard workflow
        logger.info("Using standard mode")
        state = {"question": question}
        for name, module in self.modules.items():
            # Skip planning module here as it's handled separately above
            if name == "planning":
                continue

            # Check if module is enabled globally AND in this request
            is_enabled = module.enabled
            if active_modules and name in active_modules:
                is_enabled = active_modules[name]
                
            if is_enabled:
                logs.append(f"🔄 Module '{name}': Processing...")
                state = module.process(state)
                if name == "memory" and "memory_context" in state:
                    count = len(state["memory_context"])
                    logs.append(f"  ↳ Memory Recall: Found {count} relevant items")
            else:
                logs.append(f"⏭️ Module '{name}': Skipped (Disabled)")
        
        # Invoke agent
        # Invoke agent
        messages = []
        
        # Use context from state if available (populated by MemoryModule.process)
        if "memory_context" in state:
            messages.extend(state["memory_context"])
        elif "memory" in self.modules and self.modules["memory"].enabled:
            # Only fallback if memory is actually enabled
            is_memory_enabled = self.modules["memory"].enabled
            if active_modules and "memory" in active_modules:
                is_memory_enabled = active_modules["memory"]
                
            if is_memory_enabled:
                messages.extend(self.modules["memory"].get_history())
            
        messages.append({"role": "user", "content": question})
        response = self.agent.invoke({
            "messages": messages
        })
        
        answer = response["messages"][-1].content
        # Update memory
        is_memory_enabled = False
        if "memory" in self.modules:
            is_memory_enabled = self.modules["memory"].enabled
            if active_modules and "memory" in active_modules:
                is_memory_enabled = active_modules["memory"]
                
        if is_memory_enabled:
            logs.append("💾 Memory: Updating knowledge graph")
            self.modules["memory"].update(question, answer)
            
        logger.info(f"Answer generated ({len(answer)} chars)")
        
        # Construct full prompt for display (including system prompt)
        full_prompt_display = []
        if hasattr(self, 'system_prompt'):
            full_prompt_display.append({"role": "system", "content": self.system_prompt})
        full_prompt_display.extend(messages)
        
        return {
            "answer": answer,
            "logs": logs,
            "full_prompt": full_prompt_display,
            "memory_context": state.get("memory_context", [])
        }

    def get_memory_state(self) -> dict[str, Any]:
        """Get current state of memory module."""
        if "memory" in self.modules and self.modules["memory"].enabled:
            mem = self.modules["memory"]
            return {
                "history": mem.history,
                "concepts": mem.concepts,
                "concept_index": getattr(mem, "concept_index", {}),
                "user_context": mem.user_context
            }
        return {
            "history": [],
            "concepts": {},
            "user_context": {}
        }
