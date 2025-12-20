"""Configuration management using YAML."""
import os
import logging
from pathlib import Path
from typing import Any, Literal
import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class VaultConfig(BaseModel):
    """Vault configuration."""
    path: Path
    indexed_folders: list[str] = Field(default_factory=list)
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v: Path) -> Path:
        """Ensure path is absolute."""
        return v.expanduser().resolve()


class OllamaConfig(BaseModel):
    """Ollama model configuration."""
    model: str = "qwen2.5:3b"
    base_url: str = "http://localhost:11434"


class ModelConfig(BaseModel):
    """Model configuration."""
    provider: Literal["ollama", "anthropic"] = "ollama"
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    temperature: float = 0.0
    num_ctx: int = 4096
    max_tokens: int = 2048


class AgentConfig(BaseModel):
    """Agent configuration."""
    max_iterations: int = 10
    verbose: bool = False
    timeout: int = 120


class RetrievalModuleConfig(BaseModel):
    """Retrieval module configuration."""
    enabled: bool = True
    max_results: int = 15
    max_file_lines: int = 80
    search_depth: str | int = "unlimited"


class MemoryModuleConfig(BaseModel):
    """Memory module configuration."""
    enabled: bool = True
    max_history: int = 10
    strategy: Literal["buffer", "summary"] = "buffer"


class PlanningModuleConfig(BaseModel):
    """Planning module configuration (Planner-Executor pattern)."""
    enabled: bool = False  # Disabled by default
    max_subtasks: int = 10
    max_retries_per_task: int = 2
    enable_replanning: bool = True
    verification_mode: Literal["strict", "flexible"] = "flexible"


class PlanningModuleConfig(BaseModel):
    """Planning module configuration (Planner-Executor pattern)."""
    enabled: bool = False  # Disabled by default
    max_subtasks: int = 10
    max_retries_per_task: int = 2
    enable_replanning: bool = True
    verification_mode: Literal["strict", "flexible"] = "flexible"


class ModulesConfig(BaseModel):
    """Modules configuration."""
    retrieval: RetrievalModuleConfig = Field(default_factory=RetrievalModuleConfig)
    planning: PlanningModuleConfig = Field(default_factory=PlanningModuleConfig)
    memory: MemoryModuleConfig = Field(default_factory=MemoryModuleConfig)


class LogFileConfig(BaseModel):
    """Log file configuration."""
    enabled: bool = False
    path: str = "logs/agent.log"
    max_size_mb: int = 10
    backup_count: int = 3


class LogConsoleConfig(BaseModel):
    """Log console configuration."""
    enabled: bool = True
    colorized: bool = True


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    file: LogFileConfig = Field(default_factory=LogFileConfig)
    console: LogConsoleConfig = Field(default_factory=LogConsoleConfig)


class FilesystemToolsConfig(BaseModel):
    """Filesystem tools configuration."""
    max_folder_items: int = 30
    max_search_results: int = 15
    max_grep_results: int = 10


class ToolsConfig(BaseModel):
    """Tools configuration."""
    filesystem: FilesystemToolsConfig = Field(default_factory=FilesystemToolsConfig)


class Settings(BaseModel):
    """Complete application settings."""
    vault: VaultConfig
    model: ModelConfig = Field(default_factory=ModelConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    modules: ModulesConfig = Field(default_factory=ModulesConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    
    def validate_setup(self) -> None:
        """Validate complete setup."""
        # Check vault exists
        if not self.vault.path.exists():
            raise ValueError(f"Vault path does not exist: {self.vault.path}")
        
        # Check for markdown files
        md_files = list(self.vault.path.rglob("*.md"))
        if not md_files:
            raise ValueError(f"No markdown files found in: {self.vault.path}")
        
        logger.info(f"✅ Vault validated: {len(md_files)} markdown files found")


def load_config(config_path: str = "config.yaml") -> Settings:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file (default: config.yaml)
    
    Returns:
        Settings object
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"💡 Copy config.yaml.example to config.yaml and edit it."
        )
    
    # Load YAML
    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    # Parse and validate
    try:
        settings = Settings(**config_data)
        logger.info(f"✅ Configuration loaded from {config_path}")
        return settings
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")


# Global settings instance (loaded on import)
try:
    settings = load_config()
except FileNotFoundError as e:
    logger.error(str(e))
    settings = None
