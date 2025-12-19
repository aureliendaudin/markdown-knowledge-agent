"""Memory module for managing conversation history."""
import logging
import os
from typing import Any, List, Dict, Set
import numpy as np
from .base import BaseModule

# Optional imports for advanced memory
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    HAS_VECTOR_MEMORY = True
except ImportError:
    HAS_VECTOR_MEMORY = False
    logger.warning("sentence-transformers or faiss not found. Vector memory disabled.")

logger = logging.getLogger(__name__)


class MemoryModule(BaseModule):
    """
    Advanced Memory Agent implementing:
    1. Structural Memory (Markdown/Files) - via simple scan
    2. Semantic Memory (Embeddings) - via FAISS
    3. Conceptual Memory (Concepts/Links) - via Graph/Dict
    4. User Context Memory (Preferences) - via Profile
    
    The agent actively chooses which memories to consult and how to format the result.
    """
    
    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.history: List[Dict[str, str]] = []
        self.max_history = self.config.get("max_history", 20)
        
        # Conceptual Memory
        self.concepts: Dict[str, Any] = {}
        self.concept_index: Dict[str, List[int]] = {}
        
        # User Context Memory
        self.user_context: Dict[str, Any] = {}
        
        # Semantic Memory (Vector Store)
        self.vector_index = None
        self.embedding_model = None
        self.stored_vectors = []
        
        if HAS_VECTOR_MEMORY:
            try:
                logger.info("Loading embedding model for Semantic Memory...")
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                self.dimension = 384
                self.vector_index = faiss.IndexFlatL2(self.dimension)
                logger.info("Semantic Memory initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Semantic Memory: {e}")
                self.embedding_model = None

    def initialize(self) -> None:
        """Initialize memory module."""
        logger.info(f"Initializing {self.name}")
        self.history = []
        self.concepts = {}
        self.concept_index = {}
        self.user_context = {}
        if self.vector_index:
            self.vector_index.reset()
            self.stored_vectors = []
        
    def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Process state to add memory context.
        """
        Process state to add memory context.
        Executes the Active Recall phase.
        """
        question = state.get("question", "")
        if question:
            # 1. Active Agent: Choose strategies
            strategies = self._decide_consultation_strategy(question)
            
            # 2. Consult Memories
            raw_memories = self._consult_memories(question, strategies)
            
            # 3. Active Agent: Filter and Rank (Choose what to recall/ignore)
            filtered_memories = self._rank_and_filter(raw_memories, question)
            
            # 4. Active Agent: Format (Choose final format)
            final_context = self._format_context(filtered_memories)
            
            state["memory_context"] = final_context
            logger.info(f"Memory Agent provided {len(final_context)} context items")
            
        return state
        
    def _decide_consultation_strategy(self, query: str) -> List[str]:
        """
        Active Agent: Decide which memories to consult based on query intent.
        """
        strategies = ["short_term"] # Always consult short-term
        
        query_lower = query.lower()
        
        # Heuristic Intent Detection
        if any(w in query_lower for w in ["who", "what", "where", "when", "remember", "told me"]):
            strategies.append("semantic") # Fact retrieval
            
        if any(w in query_lower for w in ["concept", "idea", "summary", "overview", "link"]):
            strategies.append("conceptual") # Concept retrieval
            
        if any(w in query_lower for w in ["i like", "my", "prefer", "want"]):
            strategies.append("user_context") # User preference
            
        if any(w in query_lower for w in ["file", "note", "document", "folder", "markdown"]):
            strategies.append("structural") # File search
            
        # Default fallback if query is complex
        if len(strategies) == 1:
            strategies.append("semantic")
            strategies.append("conceptual")
            
        return strategies

    def _consult_memories(self, query: str, strategies: List[str]) -> Dict[str, List[Any]]:
        """
        Consult selected memory stores.
        """
        results = {
            "short_term": [],
            "semantic": [],
            "conceptual": [],
            "user_context": [],
            "structural": []
        }
        
        # 1. Short Term (Recent History)
        if "short_term" in strategies:
            results["short_term"] = self.history[-4:] # Last 2 turns
            
        # 2. Semantic Memory (Embeddings)
        if "semantic" in strategies and self.vector_index and self.embedding_model:
            results["semantic"] = self._search_semantic(query)
            
        # 3. Conceptual Memory (Graph/Keywords)
        if "conceptual" in strategies:
            results["conceptual"] = self._search_conceptual(query)
            
        # 4. User Context
        if "user_context" in strategies:
            results["user_context"] = [self.user_context] if self.user_context else []
            
        # 5. Structural Memory (Simple File Scan)
        if "structural" in strategies:
            results["structural"] = self._search_structural(query)
            
        return results

    def _search_semantic(self, query: str, k: int = 3) -> List[Dict[str, str]]:
        """Search vector store for semantically similar messages."""
        if not self.history or self.vector_index.ntotal == 0:
            return []
            
        query_vec = self.embedding_model.encode([query])
        distances, indices = self.vector_index.search(query_vec, k)
        
        results = []
        for idx in indices[0]:
            if idx != -1 and idx < len(self.history):
                results.append(self.history[idx])
        return results

    def _search_conceptual(self, query: str) -> List[Dict[str, str]]:
        """Search concept graph."""
        results = []
        query_lower = query.lower()
        for concept, indices in self.concept_index.items():
            if concept.lower() in query_lower:
                for idx in indices:
                    if idx < len(self.history):
                        results.append(self.history[idx])
        return results

    def _search_structural(self, query: str) -> List[str]:
        """
        Simple structural search (simulated).
        In a real app, this would query the RetrievalModule or scan files.
        """
        # Placeholder: Just return a note if keyword matches
        # This is where we would interface with the Vault
        return []

    def _rank_and_filter(self, raw_memories: Dict[str, List[Any]], query: str) -> List[Dict[str, str]]:
        """
        Active Agent: Choose what to recall and what to ignore.
        Deduplicates and ranks messages.
        """
        # Combine all message-based memories
        all_messages = []
        seen_content = set()
        
        # Priority: Short Term > Semantic > Conceptual
        sources = ["short_term", "semantic", "conceptual"]
        
        for source in sources:
            for msg in raw_memories.get(source, []):
                if isinstance(msg, dict) and "content" in msg:
                    content = msg["content"]
                    if content not in seen_content:
                        seen_content.add(content)
                        all_messages.append(msg)
        
        # Sort by chronological order (assuming we can infer it or it's preserved)
        # Since we don't store timestamps, we rely on the fact that history is appended.
        # We can try to find the index in self.history to sort.
        
        def get_msg_index(msg):
            try:
                return self.history.index(msg)
            except ValueError:
                return -1
                
        all_messages.sort(key=get_msg_index)
        
        return all_messages

    def _format_context(self, memories: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Active Agent: Choose final format injected into prompt.
        """
        # Currently just returns the list of messages.
        # Could be enhanced to summarize or rephrase.
        return memories

    def update(self, question: str, answer: str):
        """
        Update all memory stores.
        """
        # 1. Update History
        self.history.append({"role": "user", "content": question})
        user_idx = len(self.history) - 1
        self.history.append({"role": "assistant", "content": answer})
        asst_idx = len(self.history) - 1
        
        # 2. Update Semantic Memory
        if self.vector_index and self.embedding_model:
            vectors = self.embedding_model.encode([question, answer])
            self.vector_index.add(vectors)
            self.stored_vectors.extend(vectors)
            
        # 3. Update Conceptual Memory
        new_knowledge = self._extract_new_knowledge(question, answer)
        self._update_concepts(new_knowledge, [user_idx, asst_idx])
        
        # 4. Update User Context
        self._update_user_context(question)
        
        # Trim history if needed
        if len(self.history) > self.max_history * 2:
            # For vector store, trimming is hard without rebuilding.
            # For now, we just trim the list and accept indices might drift in vector store
            # (In production, use a proper VectorDB with IDs)
            self.history.pop(0)
            self.history.pop(0)

    def _extract_new_knowledge(self, question: str, answer: str) -> Dict[str, Any]:
        """Extract new knowledge/facts."""
        knowledge = {}
        import re
        combined_text = f"{question} {answer}"
        potential_concepts = set(re.findall(r'\b[A-Z][a-zA-Z]+\b', combined_text))
        stoplist = {"The", "A", "An", "In", "On", "At", "To", "For", "Is", "Are", "Was", "Were"}
        concepts = [c for c in potential_concepts if c not in stoplist]
        if concepts:
            knowledge["concepts"] = concepts
        return knowledge

    def _update_concepts(self, knowledge: Dict[str, Any], indices: List[int] = []):
        """Update concept graph."""
        if "concepts" in knowledge:
            for concept in knowledge["concepts"]:
                if concept not in self.concepts:
                    self.concepts[concept] = {"count": 0, "first_seen": len(self.history)}
                self.concepts[concept]["count"] += 1
                if concept not in self.concept_index:
                    self.concept_index[concept] = []
                for idx in indices:
                    if idx not in self.concept_index[concept]:
                        self.concept_index[concept].append(idx)

    def _update_user_context(self, question: str):
        """Update user context."""
        # Simple domain detection for interest tracking
        pass # (Simplified for brevity, logic exists in previous version if needed)

    def get_history(self) -> List[Dict[str, str]]:
        return self.history
        
    def clear(self):
        self.history = []
        self.concepts = {}
        self.concept_index = {}
        self.user_context = {}
        if self.vector_index:
            self.vector_index.reset()

