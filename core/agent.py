"""Core agent implementation."""
import logging
from typing import Any
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from config import settings
from tools import get_all_tools
from modules import RetrievalModule, MemoryModule

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
        system_prompt = self.modules["retrieval"].get_system_prompt()
        
        return create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=system_prompt
        )
    
    def ask(self, question: str) -> dict[str, Any]:
        """Ask a question to the agent."""
        logger.info(f"Question: {question}")
        logs = []
        
        # Process through modules
        state = {"question": question}
        for name, module in self.modules.items():
            if module.enabled:
                logs.append(f"🔄 Module '{name}': Processing...")
                state = module.process(state)
                if name == "memory" and "memory_context" in state:
                    count = len(state["memory_context"])
                    logs.append(f"  ↳ Memory Recall: Found {count} relevant items")
        
        # Invoke agent
        messages = []
        
        # Use context from state if available (populated by MemoryModule.process)
        if "memory_context" in state:
            messages.extend(state["memory_context"])
        elif "memory" in self.modules and self.modules["memory"].enabled:
            messages.extend(self.modules["memory"].get_history())
            
        messages.append({"role": "user", "content": question})
        
        logs.append(f"🤖 Agent: Generating response with {len(messages)} context messages")
        
        response = self.agent.invoke({
            "messages": messages
        })
        
        answer = response["messages"][-1].content
        
        # Update memory
        if "memory" in self.modules and self.modules["memory"].enabled:
            logs.append("💾 Memory: Updating knowledge graph")
            self.modules["memory"].update(question, answer)
            
        logger.info(f"Answer generated ({len(answer)} chars)")
        
        return {
            "answer": answer,
            "logs": logs
        }
