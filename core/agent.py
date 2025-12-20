"""Core agent implementation with iterative reflection."""
import logging
from typing import Any
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from config import settings
from tools import get_all_tools
from modules import RetrievalModule
from modules.reflection import ReflectionModule

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

        if settings.modules.reflection.enabled:
            modules["reflection"] = ReflectionModule(
                config={
                    "max_iterations": settings.modules.reflection.max_iterations,
                    "acceptance_threshold": settings.modules.reflection.acceptance_threshold,
                    "enable_llm_critique": True,  # Enable LLM-based critique
                    "model": self.model  # Pass model instance for reflection
                }
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
    
    def ask(self, question: str) -> str:
        """Ask a question to the agent."""
        logger.info(f"Question: {question}")
        
        # Initialize state
        state = {
            "question": question,
            "reflection_iteration": 0
        }
        
        # Phase 1: Pre-agent modules (retrieval)
        for name, module in self.modules.items():
            if module.enabled and module.__class__.__name__ != "ReflectionModule":
                state = module.process(state)
                logger.debug(f"Module {name} processed state")
        
        # Phase 2: Iterative generation + reflection loop
        max_iterations = self.modules["reflection"].max_iterations if "reflection" in self.modules else 1
        
        for iteration in range(max_iterations + 1):
            # Generate answer (use refinement prompt if available)
            if iteration == 0:
                prompt = question
            else:
                prompt = state.get("refinement_prompt", question)
            
            response = self.agent.invoke({
                "messages": [{"role": "user", "content": prompt}]
            })
            answer = response["messages"][-1].content
            logger.info(f"Answer generated (iteration {iteration}, {len(answer)} chars)")
            
            # Store candidate answer
            state["candidate_answer"] = answer
            state["reflection_iteration"] = iteration
            
            # Phase 3: Run reflection module
            if "reflection" in self.modules and self.modules["reflection"].enabled:
                state = self.modules["reflection"].process(state)
                
                # Check if refinement is needed
                if not state.get("refinement_needed", False):
                    # Answer approved or flagged - we're done
                    break
                else:
                    # Reset refinement flag for next iteration
                    state["refinement_needed"] = False
                    logger.info(f"Starting refinement iteration {iteration + 1}")
            else:
                # No reflection module - accept answer as-is
                state["final_answer"] = answer
                break
        
        # Return final answer
        final_answer = state.get("final_answer", answer)
        
        # Log reflection stats if available
        if "reflection_history" in state:
            scores = [h["score"] for h in state["reflection_history"]]
            logger.info(f"Reflection summary: iterations={len(scores)}, scores={scores}")
        
        return final_answer