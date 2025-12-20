"""Core agent implementation with iterative reflection."""
import logging
from typing import Any
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from config import settings
from tools import get_all_tools
from modules import RetrievalModule, PlannerExecutorModule, MemoryModule, ReflectionModule

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
        # Reflection module
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
        
        # Determine if planning is enabled for this request
        is_planning_enabled = False
        if "planning" in self.modules and self.modules["planning"].enabled:
            is_planning_enabled = True
            if active_modules and "planning" in active_modules:
                is_planning_enabled = active_modules["planning"]

        # If planning module is enabled, use Planner-Executor pattern
        if is_planning_enabled:
            logger.info("Using Planner-Executor mode")
            logs.append("🧠 Strategy: Planner-Executor Mode")
            state = {"question": question}
            state = self.modules["planning"].process(state)
            answer = state.get("answer", "No answer generated")
            logger.info(f"Answer generated ({len(answer)} chars)")
            return {
                "answer": answer,
                "logs": logs
            }
        
        # Otherwise, use standard workflow
        logger.info("Using standard mode")
        state = { "question": question, "reflection_iteration": 0 }
        for name, module in self.modules.items():
            # Skip planning and reflection modules here as they are handled separately
            if name == "planning" or name == "reflection":
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

        max_iterations = self.modules["reflection"].max_iterations if "reflection" in self.modules else 1

        for iteration in range(max_iterations + 1):
            # Generate answer (use refinement prompt if available)
            if iteration == 0:
                prompt = question
            else:
                prompt = state.get("refinement_prompt", question)

            messages.append({"role": "user", "content": prompt})
            logs.append(f"🤖 Agent: Generating response with {len(messages)} context messages")
            
            response = self.agent.invoke({
                "messages": messages
            })
            answer = response["messages"][-1].content
            logger.info(f"Answer generated (iteration {iteration}, {len(answer)} chars): {answer}")

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
        
        # Final answer
        final_answer = state.get("final_answer", answer)
        
        # Log reflection stats if available
        if "reflection_history" in state:
            scores = [h["score"] for h in state["reflection_history"]]
            logger.info(f"Reflection summary: iterations={len(scores)}, scores={scores}")

        # Update memory
        is_memory_enabled = False
        if "memory" in self.modules:
            is_memory_enabled = self.modules["memory"].enabled
            if active_modules and "memory" in active_modules:
                is_memory_enabled = active_modules["memory"]
                
        if is_memory_enabled:
            logs.append("💾 Memory: Updating knowledge graph")
            self.modules["memory"].update(question, final_answer)
            
        logger.info(f"Answer generated ({len(final_answer)} chars)")
        
        # Construct full prompt for display (including system prompt)
        full_prompt_display = []
        if hasattr(self, 'system_prompt'):
            full_prompt_display.append({"role": "system", "content": self.system_prompt})
        full_prompt_display.extend(messages)
        
        return {
            "answer": final_answer,
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
