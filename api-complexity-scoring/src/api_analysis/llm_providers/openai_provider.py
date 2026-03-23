"""
OpenAI GPT-4o-mini provider implementation.

Provides structured output capabilities using OpenAI's structured output mode.
"""

import json
from typing import Any, Dict, Optional

from openai import OpenAI

from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """
    GPT-4o-mini LLM provider.
    
    Supports native structured output using OpenAI's structured output mode.
    """
    
    def __init__(self, api_key: str, **kwargs):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            **kwargs: Additional configuration
        """
        super().__init__(api_key, **kwargs)
        
        # Initialize client
        self.client = OpenAI(api_key=api_key)
        
        # Set model name
        self.model_name = kwargs.get('model_name', 'gpt-4o-mini')
    
    def analyze(
        self,
        prompt: str,
        schema: Dict[str, Any],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze API using GPT-4o-mini with structured output.
        
        Args:
            prompt: Analysis prompt
            schema: JSON schema for response
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Max output tokens (None = default)
            
        Returns:
            Structured analysis result
            
        Raises:
            Exception: If LLM call fails
        """
        try:
            # Build request parameters
            params = {
                'model': self.model_name,
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are an expert API analyst. Analyze the provided API '
                                 'documentation and respond with structured JSON data.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': temperature,
                'response_format': {
                    'type': 'json_schema',
                    'json_schema': {
                        'name': 'api_analysis',
                        'strict': True,
                        'schema': schema
                    }
                }
            }
            
            if max_tokens:
                params['max_tokens'] = max_tokens
            
            # Call API
            response = self.client.chat.completions.create(**params)
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            return result
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse OpenAI response as JSON: {e}")
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")
    
    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for GPT-4o-mini.
        
        Pricing (as of 2024):
        - Input: $0.150 per 1M tokens
        - Output: $0.600 per 1M tokens
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * 0.150
        output_cost = (output_tokens / 1_000_000) * 0.600
        return input_cost + output_cost
    
    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return 'gpt-4o-mini'
    
    @property
    def supports_structured_output(self) -> bool:
        """GPT-4o-mini supports native structured output."""
        return True
