"""
Base class for LLM providers.

Defines the interface that all LLM providers must implement.
This allows for easy addition of new LLM providers and swapping between them.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All LLM providers (Gemini, GPT, Claude) must implement this interface.
    This ensures consistent behavior across different LLM backends.
    """
    
    def __init__(self, api_key: str, **kwargs):
        """
        Initialize the LLM provider.
        
        Args:
            api_key: API key for the LLM service
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.config = kwargs
    
    @abstractmethod
    def analyze(
        self,
        prompt: str,
        schema: Dict[str, Any],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze API using LLM with structured output.
        
        Args:
            prompt: The analysis prompt containing API information
            schema: JSON schema for the expected output structure
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens in response (None = provider default)
            
        Returns:
            Dictionary containing the structured analysis result
            
        Raises:
            Exception: If the LLM call fails or returns invalid data
        """
        pass
    
    @abstractmethod
    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for token usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Get the provider name.
        
        Returns:
            Provider name (e.g., 'gemini-2.0-flash', 'gpt-4o-mini')
        """
        pass
    
    @property
    @abstractmethod
    def supports_structured_output(self) -> bool:
        """
        Check if provider supports native structured output.
        
        Returns:
            True if provider has native structured output support
        """
        pass
    
    def validate_response(self, response: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        Validate that response matches the expected schema.
        
        Args:
            response: The LLM response
            schema: Expected JSON schema
            
        Returns:
            True if response is valid
            
        Note:
            Default implementation does basic type checking.
            Override for more sophisticated validation.
        """
        # Basic validation - check that all required fields are present
        if 'properties' in schema:
            required_fields = schema.get('required', [])
            for field in required_fields:
                if field not in response:
                    return False
        return True
    
    def retry_on_failure(
        self,
        func,
        max_retries: int = 3,
        backoff_factor: float = 2.0
    ) -> Any:
        """
        Retry a function call with exponential backoff.
        
        Args:
            func: Function to retry
            max_retries: Maximum number of retries
            backoff_factor: Backoff multiplier between retries
            
        Returns:
            Result of the function call
            
        Raises:
            Exception: If all retries fail
        """
        import time
        
        last_exception = None
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = backoff_factor ** attempt
                    time.sleep(wait_time)
                    continue
                else:
                    raise last_exception
    
    def __repr__(self) -> str:
        """String representation (hides API key)."""
        return f"{self.__class__.__name__}(provider={self.provider_name}, api_key=***)"

