"""Advanced reflection module for pedagogical agent.

This implementation uses LLM-based evaluation to assess answer quality
on multiple pedagogical dimensions and can trigger re-generation.
"""
import logging
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage
from .base import BaseModule

logger = logging.getLogger(__name__)


class ReflectionModule(BaseModule):
    """Advanced reflection module with LLM-based pedagogical critique.

    Config (passed as dict) supports:
    - max_iterations: int (default: 2)
    - acceptance_threshold: float (0..1, default: 0.7)
    - enable_llm_critique: bool (default: True)
    - critique_dimensions: list of str (pedagogical aspects to evaluate)
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        cfg = config or {}
        self.max_iterations = int(cfg.get("max_iterations", 2))
        self.acceptance_threshold = float(cfg.get("acceptance_threshold", 0.7))
        self.enable_llm_critique = cfg.get("enable_llm_critique", True)
        self.model = cfg.get("model")  # LLM instance passed from agent
        
        # Pedagogical dimensions to evaluate
        self.critique_dimensions = cfg.get("critique_dimensions", [
            "factual_accuracy",      # Basé sur les sources
            "clarity",               # Compréhensibilité
            "completeness",          # Répond à toute la question
            "pedagogical_quality",   # Structure, exemples, progression
            "source_citation"        # Référence explicite aux notes
        ])

    def initialize(self) -> None:
        logger.info(
            f"Initializing {self.name} (max_iter={self.max_iterations}, "
            f"llm_critique={self.enable_llm_critique})"
        )

    def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Evaluate and potentially refine the candidate answer.
        
        Flow:
        1. Extract candidate answer and context (retrieved docs, question)
        2. Run multi-dimensional evaluation
        3. If score < threshold and iterations remain: generate refinement prompt
        4. Otherwise: approve or flag answer
        """
        candidate = state.get("candidate_answer")
        if not candidate:
            return state

        question = state.get("question", "")
        retrieved_docs = state.get("retrieved_documents", [])
        iteration = state.get("reflection_iteration", 0)

        # Run evaluation
        if self.enable_llm_critique and self.model:
            evaluation = self._llm_based_evaluation(question, candidate, retrieved_docs)
        else:
            evaluation = self._heuristic_evaluation(question, candidate, retrieved_docs)

        score = evaluation["overall_score"]
        issues = evaluation["issues"]
        
        logger.info(f"Reflection evaluation (iter {iteration}): score={score:.2f}, issues={issues}")

        # Store evaluation in state
        state.setdefault("reflection_history", []).append({
            "iteration": iteration,
            "score": score,
            "evaluation": evaluation,
            "candidate": candidate
        })

        # Decision: approve, refine, or flag
        if score >= self.acceptance_threshold:
            state["final_answer"] = candidate
            state["reflection"] = evaluation
            logger.info(f"Answer approved (score={score:.2f})")
            return state

        if iteration < self.max_iterations:
            # Generate refinement prompt and re-invoke agent
            refinement_prompt = self._build_refinement_prompt(
                question, candidate, evaluation, retrieved_docs
            )
            state["refinement_needed"] = True
            state["refinement_prompt"] = refinement_prompt
            state["reflection_iteration"] = iteration + 1
            logger.info(f"Requesting refinement (iteration {iteration + 1})")
            return state

        # Max iterations reached - flag answer as unverified
        state["final_answer"] = self._format_flagged_answer(candidate, evaluation)
        state["reflection"] = evaluation
        logger.warning(f"Max iterations reached, flagging answer (score={score:.2f})")
        return state

    def _llm_based_evaluation(
        self, 
        question: str, 
        answer: str, 
        retrieved_docs: list[dict]
    ) -> dict[str, Any]:
        """Use LLM to evaluate answer quality on multiple dimensions."""
        
        # Build context from retrieved documents
        context = self._format_retrieved_docs(retrieved_docs)
        
        system_prompt = """Tu es un critique pédagogique expert. Évalue la réponse fournie selon ces dimensions :

1. **Exactitude factuelle** (0-10) : La réponse est-elle cohérente avec les sources ?
2. **Clarté** (0-10) : Est-elle compréhensible et bien structurée ?
3. **Complétude** (0-10) : Répond-elle complètement à la question ?
4. **Qualité pédagogique** (0-10) : Contient-elle des exemples, une progression logique ?
5. **Citation des sources** (0-10) : Les notes sources sont-elles clairement référencées ?

Réponds UNIQUEMENT en JSON :
{
  "scores": {
    "factual_accuracy": <0-10>,
    "clarity": <0-10>,
    "completeness": <0-10>,
    "pedagogical_quality": <0-10>,
    "source_citation": <0-10>
  },
  "issues": ["<problème 1>", "<problème 2>", ...],
  "strengths": ["<point fort 1>", ...],
  "suggestions": ["<amélioration 1>", ...]
}"""

        user_prompt = f"""**Question de l'utilisateur :**
{question}

**Documents récupérés (sources) :**
{context}

**Réponse candidate à évaluer :**
{answer}

Évalue cette réponse selon les 5 dimensions."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            response = self.model.invoke(messages)
            
            # Parse JSON response
            import json
            evaluation_data = json.loads(response.content)
            
            # Calculate overall score (average of dimension scores, normalized to 0-1)
            scores = evaluation_data["scores"]
            overall_score = sum(scores.values()) / (len(scores) * 10)
            
            return {
                "overall_score": overall_score,
                "dimension_scores": scores,
                "issues": evaluation_data.get("issues", []),
                "strengths": evaluation_data.get("strengths", []),
                "suggestions": evaluation_data.get("suggestions", []),
                "method": "llm_critique"
            }
            
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}, falling back to heuristics")
            return self._heuristic_evaluation(question, answer, retrieved_docs)

    def _heuristic_evaluation(
        self, 
        question: str, 
        answer: str, 
        retrieved_docs: list[dict]
    ) -> dict[str, Any]:
        """Fallback: simple heuristic-based evaluation."""
        issues: list[str] = []
        score = 0.5  # Base score

        if not answer or len(answer.strip()) < 30:
            issues.append("too_short")
            score -= 0.3

        low = answer.lower()
        if any(x in low for x in ["i don't know", "no notes found", "not found"]):
            issues.append("non_answer")
            score -= 0.4

        # Check for source references
        has_sources = any(token in answer for token in [".md", "[[", "source:", "selon"])
        if not has_sources:
            issues.append("no_source_citation")
            score -= 0.2
        else:
            score += 0.2

        # Check length (pedagogical answers should be substantial)
        if len(answer) > 100:
            score += 0.2

        score = max(0.0, min(1.0, score))

        return {
            "overall_score": score,
            "dimension_scores": {},
            "issues": issues,
            "strengths": [],
            "suggestions": ["Consider using LLM-based critique for better evaluation"],
            "method": "heuristic"
        }

    def _build_refinement_prompt(
        self,
        question: str,
        candidate: str,
        evaluation: dict,
        retrieved_docs: list[dict]
    ) -> str:
        """Generate a refinement prompt based on evaluation issues."""
        
        context = self._format_retrieved_docs(retrieved_docs)
        issues = evaluation.get("issues", [])
        suggestions = evaluation.get("suggestions", [])
        
        prompt = f"""Ta réponse précédente nécessite des améliorations.

**Question originale :** {question}

**Ta réponse précédente :**
{candidate}

**Problèmes identifiés :**
{chr(10).join(f"- {issue}" for issue in issues)}

**Suggestions d'amélioration :**
{chr(10).join(f"- {sug}" for sug in suggestions)}

**Sources disponibles :**
{context}

Génère une réponse améliorée qui :
1. Corrige les problèmes identifiés
2. Cite explicitement les sources pertinentes
3. Structure clairement l'information
4. Ajoute des exemples si approprié"""

        return prompt

    def _format_retrieved_docs(self, retrieved_docs: list[dict]) -> str:
        """Format retrieved documents for context."""
        if not retrieved_docs:
            return "(Aucune source récupérée)"
        
        formatted = []
        for i, doc in enumerate(retrieved_docs, 1):
            title = doc.get("metadata", {}).get("source", f"Document {i}")
            content = doc.get("page_content", "")[:300]  # Truncate for context
            formatted.append(f"[{i}] {title}:\n{content}...")
        
        return "\n\n".join(formatted)

    def _format_flagged_answer(self, candidate: str, evaluation: dict) -> str:
        """Format an answer that didn't meet quality standards."""
        issues_text = "\n".join(f"• {issue}" for issue in evaluation.get("issues", []))
        
        return f"""Réponse non vérifiée (score: {evaluation['overall_score']:.2f})

{candidate}

---
**Note :** Cette réponse n'a pas atteint le seuil de qualité requis.

**Problèmes identifiés :**
{issues_text}

Veuillez vérifier manuellement les sources ou reformuler votre question."""