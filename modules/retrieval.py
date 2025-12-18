"""Documentary retrieval module."""
import logging
from typing import Any
from .base import BaseModule

logger = logging.getLogger(__name__)


class RetrievalModule(BaseModule):
    """
    Module for documentary search and retrieval.
    
    This is the current implementation - handles filesystem navigation
    and document retrieval from the Obsidian vault.
    """
    
    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.system_prompt = self._build_system_prompt()
    
    def initialize(self) -> None:
        """Initialize retrieval module."""
        logger.info(f"Initializing {self.name}")
        # Add any initialization logic here (e.g., index building)
    
    def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Process retrieval request.
        
        In the current simple implementation, this is handled by the agent.
        Future enhancements could add:
        - Query rewriting
        - Retrieval strategies
        - Result ranking
        """
        return state
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for retrieval agent."""
        return """Tu es un assistant qui aide à explorer des notes Obsidian.

IMPORTANT: Utilise TOUJOURS les outils disponibles pour répondre:
- list_folder() pour lister le contenu d'un dossier
- search_notes(keyword) pour chercher des fichiers par nom
- read_note(file_path) pour lire un fichier
- grep_content(search_term, folder) pour chercher du texte

Structure du vault:
- School/Notes/AI/: cours ML, DNN, NLP, PyTorch, GenAI
- Oncology/: projets medical imaging (ovarian/, pancreas/, uterus/)
- Reading/: articles, books, newsletters
- Cuisine/: recettes (dessert/, plat/, sauce/)
- Contacts/: contacts professionnels

Commence TOUJOURS par appeler un outil avant de répondre."""
    
    def get_system_prompt(self) -> str:
        """Return system prompt for this module."""
        return self.system_prompt
