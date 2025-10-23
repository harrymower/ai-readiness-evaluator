"""Claude SDK integration - handles communication with Claude."""

import asyncio
from typing import Optional, Dict
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, TextBlock, ToolUseBlock, ToolResultBlock
from ai_evaluator.config import Config


class ClaudeClientError(Exception):
    """Custom exception for Claude client errors."""
    pass


class ClaudeClient:
    """Client for interacting with Claude via the Claude Agent SDK."""

    def __init__(self, working_dir: Optional[str] = None):
        """Initialize the Claude client.

        Args:
            working_dir: Directory where Claude should create files
        """
        self.timeout = Config.CLAUDE_TIMEOUT_SECONDS
        self.model = Config.CLAUDE_MODEL
        self.debug = Config.DEBUG_MODE
        self.working_dir = working_dir or "."

        self.options = ClaudeAgentOptions(
            model=self.model,
            max_turns=10,  # Allow multiple turns for tool use
            allowed_tools=["*"],  # Allow all tools
            permission_mode="bypassPermissions",  # Auto-approve file operations
            cwd=self.working_dir  # Set working directory for file operations
        )

    def send_prompt(self, prompt: str) -> str:
        """
        Send a prompt to Claude and return the response.

        Uses the Claude Agent SDK query() function for simple one-shot queries.

        Args:
            prompt: The prompt to send to Claude

        Returns:
            str: Claude's response

        Raises:
            ClaudeClientError: If the API call fails
        """
        try:
            # Run the async function synchronously
            return asyncio.run(self._send_prompt_async(prompt))
        except Exception as e:
            raise ClaudeClientError(f"Failed to send prompt to Claude: {e}")

    async def _send_prompt_async(self, prompt: str) -> str:
        """
        Async implementation of send_prompt using ClaudeSDKClient.

        Collects all text blocks from Claude's response, including those
        that come after tool use blocks. Also handles tool use blocks
        for file creation.

        Args:
            prompt: The prompt to send to Claude

        Returns:
            str: Claude's response (all text blocks concatenated)
        """
        response_text = ""
        tool_use_blocks = []

        async with ClaudeSDKClient(options=self.options) as client:
            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text
                        elif isinstance(block, ToolUseBlock):
                            # Collect tool use blocks for debugging
                            tool_use_blocks.append({
                                'id': block.id,
                                'name': block.name,
                                'input': block.input
                            })
                            if self.debug:
                                print(f"[DEBUG] Tool use: {block.name}")

        if self.debug:
            print(f"[DEBUG] Claude response length: {len(response_text)}")
            print(f"[DEBUG] Response preview: {response_text[:200]}")
            if tool_use_blocks:
                print(f"[DEBUG] Tool use blocks: {len(tool_use_blocks)}")
                for tool in tool_use_blocks:
                    print(f"[DEBUG]   - {tool['name']}")

        return response_text

    def send_prompt_with_context(
        self,
        prompt: str,
        context_files: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Send a prompt to Claude with additional context files.

        Args:
            prompt: The prompt to send to Claude
            context_files: Dictionary of filename -> file content to include as context

        Returns:
            str: Claude's response

        Raises:
            ClaudeClientError: If the API call fails
        """
        if not context_files:
            return self.send_prompt(prompt)

        try:
            # Build context string from files
            context_str = "\n\n".join([
                f"File: {filename}\n```\n{content}\n```"
                for filename, content in context_files.items()
            ])

            # Combine context with prompt
            full_prompt = f"{context_str}\n\n{prompt}"

            return self.send_prompt(full_prompt)

        except ClaudeClientError:
            raise
        except Exception as e:
            raise ClaudeClientError(f"Failed to send prompt with context to Claude: {e}")

    def extract_code_blocks(self, response: str) -> Dict[str, list]:
        """
        Extract code blocks from Claude's response.

        Looks for markdown code blocks with language identifiers.
        Returns a list of code blocks to preserve order and handle duplicates.

        Args:
            response: Claude's response text

        Returns:
            dict: Dictionary with 'blocks' key containing list of (language, code) tuples
        """
        code_blocks = []
        lines = response.split('\n')
        current_language = None
        current_code = []
        in_code_block = False

        for line in lines:
            # Check for code block start/end
            if line.startswith('```'):
                if in_code_block:
                    # End of code block
                    if current_language:
                        code_blocks.append((current_language, '\n'.join(current_code).strip()))
                    current_language = None
                    current_code = []
                    in_code_block = False
                else:
                    # Start of code block
                    in_code_block = True
                    # Extract language identifier
                    current_language = line[3:].strip() or 'text'
            elif in_code_block:
                current_code.append(line)

        return {'blocks': code_blocks}

    def parse_response_for_code_and_tests(self, response: str) -> Dict[str, str]:
        """
        Parse Claude's response to extract main code and test code.

        First tries to extract from code blocks in the response.
        If that fails, tries to read files created by Claude's file tools.

        Args:
            response: Claude's response text

        Returns:
            dict: Dictionary with 'code' and 'tests' keys

        Raises:
            ClaudeClientError: If response doesn't contain expected code blocks
        """
        import os
        from pathlib import Path

        result = self.extract_code_blocks(response)
        blocks = result['blocks']

        # Filter for Python code blocks
        python_blocks = [(lang, code) for lang, code in blocks if lang.lower() in ['python', 'py', '']]

        # If we have at least 2 Python code blocks, use them
        if len(python_blocks) >= 2:
            return {
                'code': python_blocks[0][1],  # Get code from first Python block
                'tests': python_blocks[1][1]  # Get code from second Python block
            }

        # Otherwise, try to read files created by Claude's file tools
        working_dir = Path(self.working_dir)
        cli_tool_path = working_dir / "cli_tool.py"
        test_tool_path = working_dir / "test_cli_tool.py"

        if cli_tool_path.exists() and test_tool_path.exists():
            return {
                'code': cli_tool_path.read_text(encoding='utf-8'),
                'tests': test_tool_path.read_text(encoding='utf-8')
            }

        # If we still don't have code, raise an error
        raise ClaudeClientError(
            f"Expected at least 2 code blocks (code + tests), got {len(blocks)}. "
            f"Also checked for files at {cli_tool_path} and {test_tool_path}"
        )

    def start_session(self) -> None:
        """
        Start a new Claude session.

        Note: The Claude CLI handles session management automatically.
        This method is a placeholder for future session management.
        """
        if self.debug:
            print(f"Starting Claude session with model: {self.model}")

    def end_session(self) -> None:
        """
        End the current Claude session.

        Note: The Claude CLI handles session management automatically.
        This method is a placeholder for future session management.
        """
        if self.debug:
            print("Ending Claude session")

