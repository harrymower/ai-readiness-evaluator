"""
Documentation fetching module.

This module provides functionality to fetch, clean, and analyze API documentation
from various sources (Swagger UI, ReadTheDocs, GitHub Pages, etc.).
"""

from .documentation import (
    fetch_documentation,
    clean_html,
    detect_documentation_type,
    extract_openapi_spec_url,
    fetch_and_clean_documentation,
)

__all__ = [
    'fetch_documentation',
    'clean_html',
    'detect_documentation_type',
    'extract_openapi_spec_url',
    'fetch_and_clean_documentation',
]
