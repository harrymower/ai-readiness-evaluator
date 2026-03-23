"""
Analyzer modules for API complexity scoring.

This package contains:
- programmatic.py: Stage 1 - Objective metric extraction
- llm_analyzer.py: Stage 2 - LLM-based subjective analysis (TODO)
- documentation_fetcher.py: Documentation retrieval (TODO)
"""

from .programmatic import (
    analyze_api_programmatically,
    analyze_multiple_endpoints,
    calculate_json_depth,
    classify_depth,
    detect_pagination,
    detect_rate_limiting,
    execute_curl,
)

__all__ = [
    'analyze_api_programmatically',
    'analyze_multiple_endpoints',
    'calculate_json_depth',
    'classify_depth',
    'detect_pagination',
    'detect_rate_limiting',
    'execute_curl',
]
