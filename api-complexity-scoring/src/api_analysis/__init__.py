"""
API Metadata Analyzer - Standalone Service

A reusable Python package for automatically analyzing APIs and generating
metadata assessments using LLMs.

This package provides:
- Programmatic API analysis (objective metrics)
- LLM-based documentation analysis (subjective assessments)
- Multi-LLM support (Gemini, GPT, Claude)
- Validation and confidence scoring
- Flexible input/output formats

Usage:
    from api_analysis import APIAnalyzer, AnalyzerConfig
    
    config = AnalyzerConfig(llm_provider="gemini-2.0-flash")
    analyzer = APIAnalyzer(config)
    result = analyzer.analyze(url="...", docs_url="...")
    result.to_yaml("output.yaml")
"""

__version__ = "1.0.0"
__author__ = "Harry Mower"
__license__ = "MIT"

# Core exports (will be implemented in later issues)
# from .models import APIMetadata, AnalysisResult, AnalyzerConfig
# from .analyzers.api_analyzer import APIAnalyzer
# from .analyzers.batch_analyzer import BatchAnalyzer

__all__ = [
    "__version__",
    # "APIMetadata",
    # "AnalysisResult",
    # "AnalyzerConfig",
    # "APIAnalyzer",
    # "BatchAnalyzer",
]

