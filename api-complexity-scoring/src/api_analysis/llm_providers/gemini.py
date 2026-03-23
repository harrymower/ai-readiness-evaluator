"""
Gemini 2.0 Flash LLM provider implementation.

Provides structured output capabilities using Google's Generative AI SDK.
"""

import json
from typing import Any, Dict, Optional

import google.generativeai as genai

from .base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    """
    Gemini 2.0 Flash LLM provider.
    
    Supports native structured output using JSON schema mode.
    """
    
    def __init__(self, api_key: str, **kwargs):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Google AI API key
            **kwargs: Additional configuration
        """
        super().__init__(api_key, **kwargs)
        
        # Configure API
        genai.configure(api_key=api_key)
        
        # Set model name
        self.model_name = kwargs.get('model_name', 'gemini-2.0-flash-exp')
    
    def analyze(
        self,
        prompt: str,
        schema: Dict[str, Any],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze API using Gemini with structured output.
        
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
            # Create model with generation config
            generation_config = {
                'temperature': temperature,
                'response_mime_type': 'application/json',
                'response_schema': schema,
            }
            
            if max_tokens:
                generation_config['max_output_tokens'] = max_tokens
            
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config
            )
            
            # Generate response
            response = model.generate_content(prompt)
            
            # Parse JSON response
            result = json.loads(response.text)
            
            return result
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse Gemini response as JSON: {e}")
        except Exception as e:
            raise Exception(f"Gemini API error: {e}")
    
    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for Gemini 2.0 Flash.
        
        Pricing (as of 2024):
        - Input: $0.075 per 1M tokens (up to 128k context)
        - Output: $0.30 per 1M tokens
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * 0.075
        output_cost = (output_tokens / 1_000_000) * 0.30
        return input_cost + output_cost
    
    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return 'gemini-2.0-flash'
    
    @property
    def supports_structured_output(self) -> bool:
        """Gemini 2.0 Flash supports native structured output."""
        return True
