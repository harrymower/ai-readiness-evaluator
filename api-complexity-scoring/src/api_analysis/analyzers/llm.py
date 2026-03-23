"""
LLM-based API analysis - Stage 2.

This module uses LLMs to assess subjective API characteristics that require
understanding of documentation and context (e.g., parameter complexity,
documentation quality, error handling).
"""

import time
from typing import Any, Dict, Optional

from ..config import Config
from ..models import LLMAnalysisResult
from ..llm_providers import GeminiProvider, OpenAIProvider


# JSON Schema for LLM structured output
LLM_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "total_endpoints": {
            "type": "integer",
            "description": "Total number of API endpoints identified"
        },
        "auth_required": {
            "type": "string",
            "enum": ["yes", "no", "optional", "unknown"],
            "description": "Whether authentication is required"
        },
        "parameter_complexity": {
            "type": "string",
            "enum": ["low", "medium", "high", "unknown"],
            "description": "Complexity of request parameters"
        },
        "error_surface": {
            "type": "string",
            "enum": ["low", "medium", "high", "unknown"],
            "description": "Variety and complexity of error handling"
        },
        "error_codes_count": {
            "type": "integer",
            "description": "Number of distinct error codes documented"
        },
        "doc_coverage": {
            "type": "string",
            "enum": ["low", "medium", "high", "unknown"],
            "description": "Quality and completeness of documentation"
        },
        "reasoning": {
            "type": "object",
            "description": "Explanation for each field",
            "properties": {
                "total_endpoints": {"type": "string"},
                "auth_required": {"type": "string"},
                "parameter_complexity": {"type": "string"},
                "error_surface": {"type": "string"},
                "error_codes_count": {"type": "string"},
                "doc_coverage": {"type": "string"}
            },
            "required": [
                "total_endpoints", "auth_required", "parameter_complexity",
                "error_surface", "error_codes_count", "doc_coverage"
            ],
            "additionalProperties": False
        },
        "confidence": {
            "type": "object",
            "description": "Confidence score (0.0-1.0) for each field",
            "properties": {
                "total_endpoints": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "auth_required": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "parameter_complexity": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "error_surface": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "error_codes_count": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "doc_coverage": {"type": "number", "minimum": 0.0, "maximum": 1.0}
            },
            "required": [
                "total_endpoints", "auth_required", "parameter_complexity",
                "error_surface", "error_codes_count", "doc_coverage"
            ],
            "additionalProperties": False
        }
    },
    "required": [
        "total_endpoints", "auth_required", "parameter_complexity",
        "error_surface", "error_codes_count", "doc_coverage",
        "reasoning", "confidence"
    ],
    "additionalProperties": False
}


def build_analysis_prompt(
    api_name: str,
    doc_content: str,
    programmatic_results: Optional[Dict] = None
) -> str:
    """
    Build comprehensive analysis prompt for LLM.
    
    Args:
        api_name: Name of the API being analyzed
        doc_content: Cleaned documentation content
        programmatic_results: Optional programmatic analysis results for context
        
    Returns:
        Formatted prompt string
    """
    prompt_parts = [
        f"# API Analysis Task\n",
        f"Analyze the following API documentation for **{api_name}** and assess its complexity.\n",
        f"\n## Documentation Content\n",
        f"{doc_content[:30000]}\n",  # Limit to ~30k chars to avoid token limits
    ]
    
    if programmatic_results:
        prompt_parts.append("\n## Programmatic Analysis Results (for context)\n")
        prompt_parts.append(f"- Schema depth: {programmatic_results.get('schema_depth', 'unknown')}\n")
        prompt_parts.append(f"- Pagination: {programmatic_results.get('pagination_supported', False)}\n")
        prompt_parts.append(f"- Rate limiting: {programmatic_results.get('rate_limiting', 'unknown')}\n")
        prompt_parts.append(f"- Auth detected: {programmatic_results.get('auth_detected', False)}\n")
    
    prompt_parts.append("""
## Assessment Instructions

Please analyze the API documentation and provide the following assessments:

1. **total_endpoints** (integer): Count the total number of distinct API endpoints documented. Look for endpoint paths, routes, or methods.

2. **auth_required** (yes/no/optional/unknown): Determine if authentication is required.
   - "yes": All endpoints require authentication
   - "no": No authentication required
   - "optional": Some endpoints require auth, others don't
   - "unknown": Cannot determine from documentation

3. **parameter_complexity** (low/medium/high/unknown): Assess the complexity of request parameters.
   - "low": Simple parameters (1-3 per endpoint, basic types)
   - "medium": Moderate complexity (4-8 parameters, some nested objects)
   - "high": Complex parameters (many parameters, deep nesting, complex validation)

4. **error_surface** (low/medium/high/unknown): Assess error handling variety.
   - "low": Basic errors (1-3 error types)
   - "medium": Moderate error handling (4-7 error types)
   - "high": Comprehensive error handling (8+ error types, detailed error responses)

5. **error_codes_count** (integer): Count distinct error codes documented (e.g., 400, 401, 404, 500).

6. **doc_coverage** (low/medium/high/unknown): Assess documentation quality and completeness.
   - "low": Minimal docs, missing key information
   - "medium": Good docs, most endpoints covered
   - "high": Excellent docs, comprehensive with examples

For each field, provide:
- **reasoning**: 1-2 sentence explanation of your assessment
- **confidence**: Score from 0.0 (not confident) to 1.0 (very confident)

If you cannot determine a value from the documentation, use "unknown" and set confidence to 0.0.
""")
    
    return ''.join(prompt_parts)


def analyze_with_llm(
    api_name: str,
    documentation: str,
    programmatic_results: Optional[Dict] = None,
    llm_provider: str = 'gemini-2.0-flash',
    config: Optional[Config] = None,
    max_retries: int = 3
) -> LLMAnalysisResult:
    """
    Analyze API using LLM with retry logic and fallback.
    
    Args:
        api_name: API name
        documentation: Documentation content
        programmatic_results: Optional programmatic analysis for context
        llm_provider: LLM provider to use ('gemini-2.0-flash' or 'gpt-4o-mini')
        config: Configuration object (creates default if None)
        max_retries: Maximum retry attempts
        
    Returns:
        LLMAnalysisResult with assessments, reasoning, and confidence
        
    Raises:
        Exception: If all retries fail and fallback also fails
    """
    if config is None:
        from ..config import get_config
        config = get_config()
    
    # Build prompt
    prompt = build_analysis_prompt(api_name, documentation, programmatic_results)
    
    # Try primary provider with retries
    provider_chain = []
    
    if llm_provider == 'gemini-2.0-flash':
        provider_chain = ['gemini-2.0-flash', 'gpt-4o-mini']
    elif llm_provider == 'gpt-4o-mini':
        provider_chain = ['gpt-4o-mini']
    else:
        raise ValueError(f"Unknown LLM provider: {llm_provider}")
    
    last_error = None
    
    for provider_name in provider_chain:
        # Get API key
        try:
            api_key = config.get_api_key(provider_name)
        except ValueError as e:
            last_error = e
            continue
        
        # Create provider instance
        if provider_name == 'gemini-2.0-flash':
            provider = GeminiProvider(api_key)
        elif provider_name == 'gpt-4o-mini':
            provider = OpenAIProvider(api_key)
        else:
            continue
        
        # Retry with exponential backoff
        for attempt in range(max_retries):
            try:
                # Call LLM
                result = provider.analyze(
                    prompt=prompt,
                    schema=LLM_RESPONSE_SCHEMA,
                    temperature=0.0
                )
                
                # Validate and return
                return LLMAnalysisResult(**result)
                
            except Exception as e:
                last_error = e
                
                # If not last attempt, apply backoff
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt)  # 1s, 2s, 4s
                    time.sleep(wait_time)
                    continue
                else:
                    # Last attempt failed, try next provider
                    break
    
    # All providers failed
    raise Exception(
        f"All LLM providers failed. Last error: {last_error}"
    )
