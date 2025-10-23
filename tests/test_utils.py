"""Tests for the utils module."""

import json
import os
import pytest
import tempfile
from ai_evaluator.utils import (
    read_file, write_file, read_json, write_json,
    parse_apis_config, parse_prompts_config,
    FileError, ParseError
)


class TestFileOperations:
    """Test cases for file I/O operations."""

    def test_read_file_success(self):
        """Test reading a file successfully."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            content = read_file(temp_path)
            assert content == "test content"
        finally:
            os.unlink(temp_path)

    def test_read_file_not_found(self):
        """Test reading a non-existent file."""
        with pytest.raises(FileNotFoundError):
            read_file("/nonexistent/path/file.txt")

    def test_write_file_success(self):
        """Test writing to a file successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")
            write_file(file_path, "test content")
            
            with open(file_path, 'r') as f:
                content = f.read()
            assert content == "test content"

    def test_write_file_creates_directory(self):
        """Test that write_file creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "subdir", "test.txt")
            write_file(file_path, "test content")
            
            assert os.path.exists(file_path)
            with open(file_path, 'r') as f:
                assert f.read() == "test content"


class TestJsonOperations:
    """Test cases for JSON I/O operations."""

    def test_read_json_success(self):
        """Test reading a JSON file successfully."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({"key": "value"}, f)
            temp_path = f.name
        
        try:
            data = read_json(temp_path)
            assert data == {"key": "value"}
        finally:
            os.unlink(temp_path)

    def test_read_json_invalid(self):
        """Test reading an invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write("invalid json {")
            temp_path = f.name
        
        try:
            with pytest.raises(ParseError):
                read_json(temp_path)
        finally:
            os.unlink(temp_path)

    def test_write_json_success(self):
        """Test writing JSON to a file successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.json")
            data = {"key": "value", "number": 42}
            write_json(file_path, data)
            
            with open(file_path, 'r') as f:
                loaded = json.load(f)
            assert loaded == data

    def test_write_json_with_indent(self):
        """Test writing JSON with custom indentation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.json")
            data = {"key": "value"}
            write_json(file_path, data, indent=4)
            
            with open(file_path, 'r') as f:
                content = f.read()
            assert "    " in content  # Check for 4-space indentation


class TestApisConfigParsing:
    """Test cases for APIs configuration parsing."""

    def test_parse_apis_config_success(self):
        """Test parsing a valid APIs config file."""
        config_content = "[OPEN_METEO_WEATHER]\ncurl_command: curl -X GET \"https://api.open-meteo.com/v1/forecast\"\ndescription: Weather API\ndocumentation_url: https://open-meteo.com/en/docs\n\n[SWAPI_PEOPLE]\ncurl_command: curl -X GET \"https://swapi.dev/api/people/1/\"\ndescription: Star Wars API\ndocumentation_url: https://swapi.dev/\n"
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(config_content)
            temp_path = f.name

        try:
            result = parse_apis_config(temp_path)
            assert "OPEN_METEO_WEATHER" in result
            assert "SWAPI_PEOPLE" in result
            assert result["OPEN_METEO_WEATHER"]["curl_command"] == 'curl -X GET "https://api.open-meteo.com/v1/forecast"'
            assert result["SWAPI_PEOPLE"]["description"] == "Star Wars API"
        finally:
            os.unlink(temp_path)

    def test_parse_apis_config_with_comments(self):
        """Test parsing APIs config with comments."""
        config_content = """
# This is a comment
[API_1]
curl_command: curl -X GET "https://api.example.com"
description: Example API
# Another comment
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            result = parse_apis_config(temp_path)
            assert "API_1" in result
            assert len(result) == 1
        finally:
            os.unlink(temp_path)

    def test_parse_apis_config_empty(self):
        """Test parsing an empty APIs config file."""
        config_content = "# Only comments\n# No APIs"
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            with pytest.raises(ParseError):
                parse_apis_config(temp_path)
        finally:
            os.unlink(temp_path)

    def test_parse_apis_config_invalid_format(self):
        """Test parsing APIs config with invalid format."""
        config_content = "key: value\n[SECTION]\nkey: value"
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(config_content)
            temp_path = f.name

        try:
            with pytest.raises(ParseError):
                parse_apis_config(temp_path)
        finally:
            os.unlink(temp_path)


class TestPromptsConfigParsing:
    """Test cases for prompts configuration parsing."""

    def test_parse_prompts_config_success(self):
        """Test parsing a valid prompts config file."""
        config_content = """
[ROUND_1_CURL_ONLY]
Build a Python CLI tool that calls this API:

{curl_command}

The CLI tool should:
1. Accept command-line arguments

---

[ROUND_2_WITH_DOCS]
Build a Python CLI tool that calls this API:

{curl_command}

Here is the API documentation:
{documentation_url}
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            result = parse_prompts_config(temp_path)
            assert "ROUND_1_CURL_ONLY" in result
            assert "ROUND_2_WITH_DOCS" in result
            assert "{curl_command}" in result["ROUND_1_CURL_ONLY"]
            assert "{documentation_url}" in result["ROUND_2_WITH_DOCS"]
        finally:
            os.unlink(temp_path)

    def test_parse_prompts_config_with_separators(self):
        """Test parsing prompts config with separator lines."""
        config_content = """
[ROUND_1]
Prompt text here

---

[ROUND_2]
Another prompt
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            result = parse_prompts_config(temp_path)
            assert "ROUND_1" in result
            assert "ROUND_2" in result
            assert "---" not in result["ROUND_1"]
        finally:
            os.unlink(temp_path)

    def test_parse_prompts_config_empty(self):
        """Test parsing an empty prompts config file."""
        config_content = "# Only comments"
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            with pytest.raises(ParseError):
                parse_prompts_config(temp_path)
        finally:
            os.unlink(temp_path)

    def test_parse_prompts_config_multiline(self):
        """Test parsing prompts with multiline content."""
        config_content = """
[ROUND_1]
Line 1
Line 2
Line 3

[ROUND_2]
Another prompt
With multiple lines
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            result = parse_prompts_config(temp_path)
            assert "Line 1" in result["ROUND_1"]
            assert "Line 2" in result["ROUND_1"]
            assert "Line 3" in result["ROUND_1"]
        finally:
            os.unlink(temp_path)

