"""Utility functions - file I/O, parsing, and helper functions."""

import json
import os
from typing import Dict, Any


class FileError(Exception):
    """Custom exception for file operations."""
    pass


class ParseError(Exception):
    """Custom exception for parsing operations."""
    pass


def read_file(filepath: str) -> str:
    """
    Read a file and return its contents.

    Args:
        filepath: Path to the file to read

    Returns:
        str: File contents

    Raises:
        FileNotFoundError: If file does not exist
        FileError: If file cannot be read
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filepath}")
    except IOError as e:
        raise FileError(f"Failed to read file '{filepath}': {e}")


def write_file(filepath: str, content: str) -> None:
    """
    Write content to a file.

    Args:
        filepath: Path to the file to write
        content: Content to write

    Raises:
        FileError: If file cannot be written
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except IOError as e:
        raise FileError(f"Failed to write file '{filepath}': {e}")


def read_json(filepath: str) -> Dict[str, Any]:
    """
    Read a JSON file and return parsed data.

    Args:
        filepath: Path to the JSON file

    Returns:
        dict: Parsed JSON contents

    Raises:
        FileNotFoundError: If file does not exist
        ParseError: If file is not valid JSON
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filepath}")
    except json.JSONDecodeError as e:
        raise ParseError(f"Invalid JSON in file '{filepath}': {e}")


def write_json(filepath: str, data: Dict[str, Any], indent: int = 2) -> None:
    """
    Write data to a JSON file.

    Args:
        filepath: Path to the JSON file
        data: Dictionary to write
        indent: JSON indentation level (default: 2)

    Raises:
        FileError: If file cannot be written
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)
    except (IOError, TypeError, ValueError) as e:
        raise FileError(f"Failed to write JSON file '{filepath}': {e}")


def parse_apis_config(filepath: str) -> Dict[str, Dict[str, str]]:
    """
    Parse APIs configuration file in INI-like format.

    Expected format:
    [API_NAME]
    curl_command: curl -X GET "..."
    description: API description
    documentation_url: https://...
    postman_collection_url: https://...
    example_prompt_url: https://...

    Args:
        filepath: Path to the APIs config file

    Returns:
        dict: Parsed API configurations

    Raises:
        FileNotFoundError: If file does not exist
        ParseError: If config format is invalid
    """
    try:
        content = read_file(filepath)
    except FileNotFoundError:
        raise

    apis = {}
    current_api = None

    for line in content.split('\n'):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue

        # Parse section header [API_NAME]
        if line.startswith('[') and line.endswith(']'):
            current_api = line[1:-1]
            apis[current_api] = {}
            continue

        # Parse key-value pairs (using : as separator)
        if ':' in line and current_api:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            apis[current_api][key] = value
        elif ':' in line and not current_api:
            raise ParseError("Found key-value pair before any section header")

    if not apis:
        raise ParseError("No API configurations found in config file")

    return apis


def parse_prompts_config(filepath: str) -> Dict[str, str]:
    """
    Parse prompts configuration file.

    Expected format:
    [ROUND_1_CURL_ONLY]
    Build a Python CLI tool that calls this API:
    ...

    [ROUND_2_WITH_DOCS]
    ...

    Args:
        filepath: Path to the prompts config file

    Returns:
        dict: Parsed prompt templates

    Raises:
        FileNotFoundError: If file does not exist
        ParseError: If config format is invalid
    """
    try:
        content = read_file(filepath)
    except FileNotFoundError:
        raise

    prompts = {}
    current_prompt = None
    current_content = []

    for line in content.split('\n'):
        # Parse section header [ROUND_X]
        if line.startswith('[') and line.endswith(']'):
            # Save previous prompt if exists
            if current_prompt:
                prompts[current_prompt] = '\n'.join(current_content).strip()

            current_prompt = line[1:-1]
            current_content = []
        elif current_prompt:
            # Skip separator lines
            if line.strip() == '---':
                continue
            current_content.append(line)

    # Save last prompt
    if current_prompt:
        prompts[current_prompt] = '\n'.join(current_content).strip()

    if not prompts:
        raise ParseError("No prompt templates found in config file")

    return prompts

