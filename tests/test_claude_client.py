"""Tests for the claude_client module."""

import pytest
from unittest.mock import patch
from ai_evaluator.claude_client import ClaudeClient, ClaudeClientError
from ai_evaluator.config import Config


class TestClaudeClientInitialization:
    """Test cases for ClaudeClient initialization."""

    def test_client_initialization(self):
        """Test that client initializes correctly."""
        client = ClaudeClient()
        assert client.timeout == Config.CLAUDE_TIMEOUT_SECONDS
        assert client.model == Config.CLAUDE_MODEL
        assert client.debug == Config.DEBUG_MODE

    def test_client_uses_config_values(self):
        """Test that client uses configuration values."""
        client = ClaudeClient()
        assert client.model == "claude-3-5-sonnet-20241022"
        assert client.timeout == 180


class TestSendPrompt:
    """Test cases for sending prompts to Claude."""

    @patch('ai_evaluator.claude_client.asyncio.run')
    def test_send_prompt_success(self, mock_asyncio_run):
        """Test successful prompt sending."""
        # Mock the async response
        mock_asyncio_run.return_value = "Claude's response"

        client = ClaudeClient()
        response = client.send_prompt("Test prompt")

        assert response == "Claude's response"
        mock_asyncio_run.assert_called_once()

    @patch('ai_evaluator.claude_client.asyncio.run')
    def test_send_prompt_strips_whitespace(self, mock_asyncio_run):
        """Test that response is returned as-is from API."""
        mock_asyncio_run.return_value = "Claude's response"

        client = ClaudeClient()
        response = client.send_prompt("Test prompt")

        assert response == "Claude's response"

    @patch('ai_evaluator.claude_client.asyncio.run')
    def test_send_prompt_error(self, mock_asyncio_run):
        """Test error handling when API call fails."""
        mock_asyncio_run.side_effect = Exception("API error")

        client = ClaudeClient()
        with pytest.raises(ClaudeClientError) as exc_info:
            client.send_prompt("Test prompt")

        assert "Failed to send prompt" in str(exc_info.value)

    @patch('ai_evaluator.claude_client.asyncio.run')
    def test_send_prompt_timeout(self, mock_asyncio_run):
        """Test timeout handling."""
        mock_asyncio_run.side_effect = Exception("Request timeout")

        client = ClaudeClient()
        with pytest.raises(ClaudeClientError) as exc_info:
            client.send_prompt("Test prompt")

        assert "Failed to send prompt" in str(exc_info.value)

    @patch('ai_evaluator.claude_client.asyncio.run')
    def test_send_prompt_not_found(self, mock_asyncio_run):
        """Test handling when API key is not configured."""
        mock_asyncio_run.side_effect = Exception("API key not found")

        client = ClaudeClient()
        with pytest.raises(ClaudeClientError) as exc_info:
            client.send_prompt("Test prompt")

        assert "Failed to send prompt" in str(exc_info.value)


class TestSendPromptWithContext:
    """Test cases for sending prompts with context files."""

    @patch('ai_evaluator.claude_client.asyncio.run')
    def test_send_prompt_with_context_success(self, mock_asyncio_run):
        """Test successful prompt sending with context."""
        mock_asyncio_run.return_value = "Claude's response"

        client = ClaudeClient()
        context = {"file.txt": "content"}
        response = client.send_prompt_with_context("Test prompt", context)

        assert response == "Claude's response"
        # Verify that asyncio.run was called with the combined prompt
        mock_asyncio_run.assert_called_once()

    @patch('ai_evaluator.claude_client.asyncio.run')
    def test_send_prompt_with_context_no_files(self, mock_asyncio_run):
        """Test that no context falls back to regular send_prompt."""
        mock_asyncio_run.return_value = "Claude's response"

        client = ClaudeClient()
        response = client.send_prompt_with_context("Test prompt", None)

        assert response == "Claude's response"

    @patch('ai_evaluator.claude_client.asyncio.run')
    def test_send_prompt_with_context_error(self, mock_asyncio_run):
        """Test error handling with context."""
        mock_asyncio_run.side_effect = Exception("API error")

        client = ClaudeClient()
        context = {"file.txt": "content"}

        with pytest.raises(ClaudeClientError):
            client.send_prompt_with_context("Test prompt", context)


class TestExtractCodeBlocks:
    """Test cases for extracting code blocks from responses."""

    def test_extract_single_code_block(self):
        """Test extracting a single code block."""
        response = "Here's the code:\n```python\nprint(\"hello\")\n```"
        client = ClaudeClient()
        result = client.extract_code_blocks(response)
        blocks = result['blocks']

        assert len(blocks) == 1
        assert blocks[0][0] == "python"
        assert blocks[0][1] == 'print("hello")'

    def test_extract_multiple_code_blocks(self):
        """Test extracting multiple code blocks."""
        response = "Here's Python code:\n```python\nprint(\"hello\")\n```\n\nAnd here's JavaScript:\n```javascript\nconsole.log(\"hello\");\n```"
        client = ClaudeClient()
        result = client.extract_code_blocks(response)
        blocks = result['blocks']

        assert len(blocks) == 2
        assert blocks[0][0] == "python"
        assert blocks[0][1] == 'print("hello")'
        assert blocks[1][0] == "javascript"
        assert blocks[1][1] == 'console.log("hello");'

    def test_extract_code_block_no_language(self):
        """Test extracting code block without language identifier."""
        response = "Here's some code:\n```\nsome code\n```"
        client = ClaudeClient()
        result = client.extract_code_blocks(response)
        blocks = result['blocks']

        assert len(blocks) == 1
        assert blocks[0][0] == "text"
        assert blocks[0][1] == "some code"

    def test_extract_multiline_code_block(self):
        """Test extracting multiline code blocks."""
        response = "```python\ndef hello():\n    print(\"hello\")\n    return True\n```"
        client = ClaudeClient()
        result = client.extract_code_blocks(response)
        blocks = result['blocks']

        assert len(blocks) == 1
        assert blocks[0][0] == "python"
        assert "def hello():" in blocks[0][1]
        assert "return True" in blocks[0][1]

    def test_extract_no_code_blocks(self):
        """Test response with no code blocks."""
        response = "This is just text with no code blocks."
        client = ClaudeClient()
        result = client.extract_code_blocks(response)
        blocks = result['blocks']

        assert len(blocks) == 0


class TestParseResponseForCodeAndTests:
    """Test cases for parsing code and tests from response."""

    def test_parse_code_and_tests_success(self):
        """Test successful parsing of code and tests."""
        response = "Here's the CLI tool:\n```python\n# Main code\nprint(\"hello\")\n```\n\nAnd here are the tests:\n```python\n# Test code\ndef test_hello():\n    assert True\n```"
        client = ClaudeClient()
        result = client.parse_response_for_code_and_tests(response)

        assert "code" in result
        assert "tests" in result
        assert 'print("hello")' in result["code"]
        assert "def test_hello():" in result["tests"]

    def test_parse_insufficient_code_blocks(self):
        """Test error when response has insufficient code blocks."""
        response = """Only one code block:
```python
print("hello")
```
"""
        client = ClaudeClient()
        
        with pytest.raises(ClaudeClientError) as exc_info:
            client.parse_response_for_code_and_tests(response)
        
        assert "Expected at least 2 code blocks" in str(exc_info.value)

    def test_parse_no_code_blocks(self):
        """Test error when response has no code blocks."""
        response = "This is just text with no code blocks."
        client = ClaudeClient()
        
        with pytest.raises(ClaudeClientError):
            client.parse_response_for_code_and_tests(response)


class TestSessionManagement:
    """Test cases for session management."""

    def test_start_session(self, capsys):
        """Test starting a session."""
        original_debug = Config.DEBUG_MODE
        Config.DEBUG_MODE = True
        
        try:
            client = ClaudeClient()
            client.start_session()
            captured = capsys.readouterr()
            
            assert "Starting Claude session" in captured.out
        finally:
            Config.DEBUG_MODE = original_debug

    def test_end_session(self, capsys):
        """Test ending a session."""
        original_debug = Config.DEBUG_MODE
        Config.DEBUG_MODE = True
        
        try:
            client = ClaudeClient()
            client.end_session()
            captured = capsys.readouterr()
            
            assert "Ending Claude session" in captured.out
        finally:
            Config.DEBUG_MODE = original_debug

    def test_start_session_no_debug(self, capsys):
        """Test that session start doesn't print without debug mode."""
        original_debug = Config.DEBUG_MODE
        Config.DEBUG_MODE = False
        
        try:
            client = ClaudeClient()
            client.start_session()
            captured = capsys.readouterr()
            
            assert captured.out == ""
        finally:
            Config.DEBUG_MODE = original_debug

