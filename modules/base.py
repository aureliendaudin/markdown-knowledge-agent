"""Base interface for agent modules."""
from abc import ABC, abstractmethod
from typing import Any


class BaseModule(ABC):
    """
    Abstract base class for agent modules.
    
    All modules (retrieval, memory, reasoning) should inherit from this.
    """
    
    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize module with optional configuration.
        
        Args:
            config: Module-specific configuration
        """
        self.config = config or {}
        self.enabled = True
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the module (load resources, setup, etc.)."""
        pass
    
    @abstractmethod
    def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Process agent state and return updated state.
        
        Args:
            state: Current agent state
        
        Returns:
            Updated agent state
        """
        pass
    
    def enable(self) -> None:
        """Enable this module."""
        self.enabled = True
    
    def disable(self) -> None:
        """Disable this module."""
        self.enabled = False
    
    @property
    def name(self) -> str:
        """Return module name."""
        return self.__class__.__name__
