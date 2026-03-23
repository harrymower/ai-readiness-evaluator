"""
Outputs module for exporting analysis results.

Supports YAML, JSON, and other output formats.
"""

from .yaml_generator import generate_yaml_entry, generate_yaml_file

__all__ = ['generate_yaml_entry', 'generate_yaml_file']
