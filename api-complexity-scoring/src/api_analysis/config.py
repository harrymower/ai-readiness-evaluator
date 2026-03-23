"""
Configuration management for API Metadata Analyzer.

Handles:
- Environment variable loading
- API key management for LLM providers
- Configuration validation
- Default settings
"""

import os
from typing import Optional
from dotenv import load_dotenv


class Config:
    """
    Configuration manager for API Metadata Analyzer.
    
    Loads configuration from environment variables and provides
    validated access to API keys and settings.
    """
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            env_file: Path to .env file (optional). If None, uses default .env
        """
        # Load environment variables from .env file
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()  # Loads from .env in current directory
        
        # Load API keys
        self._gemini_api_key = os.getenv('GEMINI_API_KEY')
        self._openai_api_key = os.getenv('OPENAI_API_KEY')
        self._anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Load optional settings
        self._default_llm_provider = os.getenv('DEFAULT_LLM_PROVIDER', 'gemini-2.0-flash')
        self._confidence_threshold = float(os.getenv('CONFIDENCE_THRESHOLD', '0.7'))
        self._timeout_seconds = int(os.getenv('TIMEOUT_SECONDS', '30'))
        self._max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self._verbose = os.getenv('VERBOSE', 'false').lower() == 'true'
    
    @property
    def gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key."""
        return self._gemini_api_key
    
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key."""
        return self._openai_api_key
    
    @property
    def anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key."""
        return self._anthropic_api_key
    
    @property
    def default_llm_provider(self) -> str:
        """Get default LLM provider."""
        return self._default_llm_provider
    
    @property
    def confidence_threshold(self) -> float:
        """Get confidence threshold."""
        return self._confidence_threshold
    
    @property
    def timeout_seconds(self) -> int:
        """Get timeout in seconds."""
        return self._timeout_seconds
    
    @property
    def max_retries(self) -> int:
        """Get max retries."""
        return self._max_retries
    
    @property
    def verbose(self) -> bool:
        """Get verbose flag."""
        return self._verbose
    
    def validate_llm_provider(self, provider: str) -> None:
        """
        Validate that API key is available for the specified LLM provider.
        
        Args:
            provider: LLM provider name
            
        Raises:
            ValueError: If API key is not configured for the provider
        """
        if provider == 'gemini-2.0-flash':
            if not self.gemini_api_key:
                raise ValueError(
                    "GEMINI_API_KEY not found in environment variables. "
                    "Please set it in your .env file or environment."
                )
        elif provider == 'gpt-4o-mini':
            if not self.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY not found in environment variables. "
                    "Please set it in your .env file or environment."
                )
        elif provider == 'claude-3.5-sonnet':
            if not self.anthropic_api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY not found in environment variables. "
                    "Please set it in your .env file or environment."
                )
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    
    def get_api_key(self, provider: str) -> str:
        """
        Get API key for the specified LLM provider.
        
        Args:
            provider: LLM provider name
            
        Returns:
            API key for the provider
            
        Raises:
            ValueError: If API key is not configured
        """
        self.validate_llm_provider(provider)
        
        if provider == 'gemini-2.0-flash':
            return self.gemini_api_key
        elif provider == 'gpt-4o-mini':
            return self.openai_api_key
        elif provider == 'claude-3.5-sonnet':
            return self.anthropic_api_key
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    
    def __repr__(self) -> str:
        """String representation (hides API keys)."""
        return (
            f"Config("
            f"gemini_key={'***' if self.gemini_api_key else 'None'}, "
            f"openai_key={'***' if self.openai_api_key else 'None'}, "
            f"anthropic_key={'***' if self.anthropic_api_key else 'None'}, "
            f"default_provider={self.default_llm_provider}, "
            f"confidence_threshold={self.confidence_threshold}"
            f")"
        )


# Global config instance (can be overridden)
_global_config: Optional[Config] = None


def get_config(env_file: Optional[str] = None) -> Config:
    """
    Get global configuration instance.
    
    Args:
        env_file: Path to .env file (optional)
        
    Returns:
        Config instance
    """
    global _global_config
    if _global_config is None or env_file is not None:
        _global_config = Config(env_file)
    return _global_config

