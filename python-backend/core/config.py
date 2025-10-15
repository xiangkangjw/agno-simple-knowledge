"""Configuration management for the knowledge management system."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv

class Config:
    """Configuration manager for the knowledge management system."""

    def __init__(self, config_path: str = "../config.yaml"):
        """Initialize configuration manager.

        Args:
            config_path: Path to the configuration YAML file
        """
        load_dotenv()
        # Resolve path relative to the python-backend directory
        self.config_path = Path(__file__).parent.parent / config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Expand user paths in target directories
        if 'indexing' in config and 'target_directories' in config['indexing']:
            config['indexing']['target_directories'] = [
                os.path.expanduser(path)
                for path in config['indexing']['target_directories']
            ]

        return config

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.

        Args:
            key_path: Dot-separated path to configuration key (e.g., 'indexing.chunk_size')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def get_openai_api_key(self) -> str:
        """Get OpenAI API key from environment variables."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key or api_key == 'your_openai_api_key_here':
            raise ValueError(
                "OPENAI_API_KEY environment variable is required!\n"
                "Please set a valid OpenAI API key in your .env file.\n"
                "Get your API key from: https://platform.openai.com/api-keys"
            )
        return api_key

    @property
    def target_directories(self) -> List[str]:
        """Get list of target directories for document indexing."""
        return self.get('indexing.target_directories', [])

    @property
    def file_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return self.get('indexing.file_extensions', ['.txt', '.md', '.pdf'])

    @property
    def storage_path(self) -> str:
        """Get ChromaDB storage path."""
        # Make storage path relative to the backend directory
        storage_path = self.get('indexing.storage_path', './chroma_db')
        if not os.path.isabs(storage_path):
            storage_path = str(Path(__file__).parent.parent / storage_path)
        return storage_path

    @property
    def collection_name(self) -> str:
        """Get ChromaDB collection name."""
        return self.get('indexing.collection_name', 'knowledge_base')

    @property
    def enable_debug(self) -> bool:
        """Return True when debug mode is enabled."""
        value = self.get('system.enable_debug', False)

        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized in {"1", "true", "yes", "on"}

        return bool(value)

    @property
    def log_level(self) -> int:
        """Get the configured logging level."""
        level_name = self.log_level_name
        return getattr(logging, level_name, logging.INFO)

    @property
    def log_level_name(self) -> str:
        """Get the configured logging level name."""
        level = self.get('system.log_level', 'INFO')

        if isinstance(level, str):
            level_name = level.strip().upper() or 'INFO'
        elif isinstance(level, int):
            level_name = logging.getLevelName(level)
            if not isinstance(level_name, str):
                level_name = 'INFO'
        else:
            level_name = 'INFO'

        if self.enable_debug and level_name != 'DEBUG':
            return 'DEBUG'

        return level_name

    @property
    def chunk_size(self) -> int:
        """Get document chunk size."""
        return self.get('indexing.chunk_size', 1024)

    @property
    def chunk_overlap(self) -> int:
        """Get document chunk overlap."""
        return self.get('indexing.chunk_overlap', 200)

    @property
    def openai_model(self) -> str:
        """Get OpenAI model name."""
        return self.get('openai.model', 'gpt-3.5-turbo')

    @property
    def embedding_model(self) -> str:
        """Get OpenAI embedding model name."""
        return self.get('openai.embedding_model', 'text-embedding-ada-002')

    @property
    def temperature(self) -> float:
        """Get OpenAI temperature setting."""
        return self.get('openai.temperature', 0.7)

    @property
    def max_tokens(self) -> int:
        """Get OpenAI max tokens setting."""
        return self.get('openai.max_tokens', 1000)

    @property
    def max_results(self) -> int:
        """Get maximum number of search results."""
        return self.get('system.max_results', 10)

    def save_config(self) -> None:
        """Save current configuration to file."""
        with open(self.config_path, 'w') as f:
            yaml.safe_dump(self.config, f, default_flow_style=False)

# Global configuration instance
config = Config()
