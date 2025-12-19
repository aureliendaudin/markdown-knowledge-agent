"""Memory module for managing conversation history."""
import logging
from typing import Any, List, Dict
from .base import BaseModule

logger = logging.getLogger(__name__)


class MemoryModule(BaseModule):
    """
    Module for managing agent memory and conversation history.
    
    Implements a sophisticated recall and update flow:
    Recall: detect_domain -> retrieve -> score -> compress
    Update: extract_knowledge -> update_concepts -> update_user_context
    """
    
    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.history: List[Dict[str, str]] = []
        self.max_history = self.config.get("max_history", 10)
        self.concepts: Dict[str, Any] = {}
        self.user_context: Dict[str, Any] = {}
        
    def initialize(self) -> None:
        """Initialize memory module."""
        logger.info(f"Initializing {self.name} with max_history={self.max_history}")
        self.history = []
        self.concepts = {}
        self.user_context = {}
        
    def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Process state to add memory context.
        Executes the Recall phase.
        """
        question = state.get("question", "")
        if question:
            # Execute Recall Flow
            context_messages = self.recall(question)
            state["memory_context"] = context_messages
            logger.info(f"Memory recall provided {len(context_messages)} messages")
            
        return state
        
    def recall(self, query: str) -> List[Dict[str, str]]:
        """
        Execute the recall flow:
        detect_domain -> retrieve_candidates -> score_relevance -> compress_context
        """
        domain = self._detect_domain(query)
        candidates = self._retrieve_candidates(query, domain)
        scored_candidates = self._score_relevance(candidates, query)
        final_context = self._compress_context(scored_candidates)
        
        return final_context

    # Going further: Could also use LLM for domain detection
    def _detect_domain(self, query: str) -> str:
        """
        Detect the domain of the query using keyword matching.
        Returns one of: 'ai', 'medical', 'cooking', 'reading', 'professional', 'general'
        """
        query_lower = query.lower()
        
        domains = {
            "ai": ["ai", "ml", "deep learning", "nlp", "pytorch", "genai", "llm", "neural", "model", "training"],
            "medical": ["oncology", "cancer", "tumor", "medical", "imaging", "ovarian", "pancreas", "uterus", "patient"],
            "cooking": ["recipe", "cuisine", "cook", "ingredient", "dish", "meal", "food", "dessert", "sauce"],
            "reading": ["book", "article", "paper", "read", "newsletter", "author", "literature"],
            "professional": ["contact", "email", "phone", "meeting", "work", "job", "career", "linkedin"]
        }
        
        for domain, keywords in domains.items():
            if any(keyword in query_lower for keyword in keywords):
                logger.info(f"Detected domain: {domain}")
                return domain
                
        return "general"

    # Going further: Implement using vector embeddings and cosine similarity
    def _retrieve_candidates(self, query: str, domain: str) -> List[Dict[str, str]]:
        """
        Retrieve candidate interactions from history.
        Filters history based on domain relevance if applicable.
        """
        if not self.history:
            return []
            
        # If domain is general, return recent history
        if domain == "general":
            return self.history[-10:]  # Return last 5 interactions (10 messages)
            
        # For specific domains, we could filter history if we had tagged it
        # For now, we'll do a simple keyword search in the history
        candidates = []
        query_terms = set(query.lower().split())
        
        # Iterate through history in pairs (user, assistant)
        for i in range(0, len(self.history), 2):
            if i + 1 >= len(self.history):
                break
                
            user_msg = self.history[i]
            asst_msg = self.history[i+1]
            
            # Check if this interaction is relevant to the query or domain
            content = (user_msg["content"] + " " + asst_msg["content"]).lower()
            
            # Simple relevance check: overlap of terms or domain match
            # In a real system, this would use vector similarity
            if any(term in content for term in query_terms) or domain in content:
                candidates.append(user_msg)
                candidates.append(asst_msg)
                
        # If we found nothing specific, fall back to recent history
        if not candidates:
            return self.history[-6:]
            
        return candidates

    def _score_relevance(self, candidates: List[Dict[str, str]], query: str) -> List[Dict[str, str]]:
        """
        Score candidates based on relevance to the query.
        Selects the top relevant interactions but preserves their chronological order.
        """
        if not candidates:
            return []
            
        query_terms = set(query.lower().split())
        scored_interactions = []
        
        # Group into pairs and score
        for i in range(0, len(candidates), 2):
            if i + 1 >= len(candidates):
                break
                
            user_msg = candidates[i]
            asst_msg = candidates[i+1]
            
            content = (user_msg["content"] + " " + asst_msg["content"]).lower()
            content_terms = set(content.split())
            
            # Score = number of overlapping terms
            overlap = len(query_terms.intersection(content_terms))
            
            # Store with original index to restore order later
            scored_interactions.append({
                "index": i,
                "score": overlap,
                "msgs": [user_msg, asst_msg]
            })
            
        # Sort by score to pick the best ones
        # We use a stable sort, so ties (e.g. 0 score) preserve relative order (recency usually)
        scored_interactions.sort(key=lambda x: x["score"], reverse=True)
        
        # Keep top K (e.g., 5 interactions = 10 messages)
        # This ensures we don't overload the context window
        top_k = 5
        selected = scored_interactions[:top_k]
        
        # Re-sort by index to restore chronological order
        # This is crucial for the LLM to understand the flow of conversation
        selected.sort(key=lambda x: x["index"])
        
        # Flatten
        final_candidates = []
        for item in selected:
            final_candidates.extend(item["msgs"])
            
        return final_candidates

    def _compress_context(self, candidates: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Compress context to fit token limits.
        Currently implements a sliding window approach, but designed to support
        summarization in the future.
        """
        # If we are within limits, return as is
        # Assuming roughly 4 chars per token, 2000 chars ~ 500 tokens
        total_chars = sum(len(m["content"]) for m in candidates)
        max_chars = 4000  # Conservative limit
        
        if total_chars <= max_chars:
            return candidates
            
        # If we exceed limits, we need to trim
        # We prioritize keeping the most recent messages in the candidate list
        # (Note: candidates are already sorted chronologically)
        compressed = []
        current_chars = 0
        
        # Iterate backwards to keep most recent
        for msg in reversed(candidates):
            msg_len = len(msg["content"])
            if current_chars + msg_len > max_chars:
                break
            compressed.insert(0, msg)
            current_chars += msg_len
            
        return compressed
        
    def get_history(self) -> List[Dict[str, str]]:
        """Return current history (fallback method)."""
        return self.history
        
    def update(self, question: str, answer: str):
        """
        Add an interaction to memory.
        Executes the Update flow:
        extract_new_knowledge -> update_concepts -> update_user_context
        """
        # 1. Standard History Update
        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": answer})
        
        # 2. Execute Update Flow
        new_knowledge = self._extract_new_knowledge(question, answer)
        self._update_concepts(new_knowledge)
        self._update_user_context(question)
        
        # Trim history if needed (keep pairs)
        while len(self.history) > self.max_history * 2:
            self.history.pop(0)
            self.history.pop(0)

    def _extract_new_knowledge(self, question: str, answer: str) -> Dict[str, Any]:
        """
        Extract new knowledge/facts from the interaction.
        Uses simple heuristic extraction for now.
        """
        knowledge = {}
        
        # Extract potential entities/concepts (capitalized words)
        # This is a very basic heuristic
        import re
        combined_text = f"{question} {answer}"
        potential_concepts = set(re.findall(r'\b[A-Z][a-zA-Z]+\b', combined_text))
        
        # Filter out common words (very basic stoplist)
        stoplist = {"The", "A", "An", "In", "On", "At", "To", "For", "Is", "Are", "Was", "Were"}
        concepts = [c for c in potential_concepts if c not in stoplist]
        
        if concepts:
            knowledge["concepts"] = concepts
            
        # Detect user preferences (e.g., "I like", "I prefer")
        if "i like" in question.lower() or "i prefer" in question.lower():
            knowledge["user_preference"] = question
            
        return knowledge

    def _update_concepts(self, knowledge: Dict[str, Any]):
        """
        Update internal concept graph with new knowledge.
        Tracks frequency of concepts to identify key topics.
        """
        if "concepts" in knowledge:
            for concept in knowledge["concepts"]:
                if concept not in self.concepts:
                    self.concepts[concept] = {"count": 0, "first_seen": len(self.history)}
                self.concepts[concept]["count"] += 1
                
        logger.debug(f"Updated concepts: {len(self.concepts)} total")

    def _update_user_context(self, question: str):
        """
        Update user preferences or context based on query.
        Maintains a simple profile of user interests.
        """
        # Detect domain of current query to update interest profile
        domain = self._detect_domain(question)
        if domain != "general":
            if "interests" not in self.user_context:
                self.user_context["interests"] = {}
            
            if domain not in self.user_context["interests"]:
                self.user_context["interests"][domain] = 0
            self.user_context["interests"][domain] += 1
            
        logger.debug(f"Updated user context: {self.user_context}")
            
    def clear(self):
        """Clear memory."""
        self.history = []
        self.concepts = {}
        self.user_context = {}
