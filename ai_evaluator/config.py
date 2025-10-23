"""Configuration module - loads and validates environment variables."""

import os
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass


class Config:
    """Application configuration loaded from environment variables."""

    # Claude Configuration
    CLAUDE_TIMEOUT_SECONDS = int(os.getenv("CLAUDE_TIMEOUT_SECONDS", "180"))
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-haiku-20241022")

    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # File Paths
    APIS_CONFIG_FILE = os.getenv("APIS_CONFIG_FILE", "config/apis.txt")
    PROMPTS_CONFIG_FILE = os.getenv("PROMPTS_CONFIG_FILE", "config/prompts.txt")
    RESULTS_DIR = os.getenv("RESULTS_DIR", "results")

    # Application Settings
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

    @classmethod
    def validate(cls) -> None:
        """
        Validate that all required configuration is present and valid.

        Raises:
            ConfigError: If any required configuration is missing or invalid
        """
        errors = []

        # Validate file paths exist
        if not os.path.exists(cls.APIS_CONFIG_FILE):
            errors.append(f"APIs config file not found: {cls.APIS_CONFIG_FILE}")

        if not os.path.exists(cls.PROMPTS_CONFIG_FILE):
            errors.append(f"Prompts config file not found: {cls.PROMPTS_CONFIG_FILE}")

        # Validate Claude timeout is positive
        if cls.CLAUDE_TIMEOUT_SECONDS <= 0:
            errors.append(f"CLAUDE_TIMEOUT_SECONDS must be positive, got: {cls.CLAUDE_TIMEOUT_SECONDS}")

        # Validate Claude model is not empty
        if not cls.CLAUDE_MODEL or not cls.CLAUDE_MODEL.strip():
            errors.append("CLAUDE_MODEL cannot be empty")

        # Raise all errors at once
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ConfigError(error_message)

        # Ensure results directory exists
        try:
            os.makedirs(cls.RESULTS_DIR, exist_ok=True)
        except OSError as e:
            raise ConfigError(f"Failed to create results directory '{cls.RESULTS_DIR}': {e}")

    @classmethod
    def get_summary(cls) -> str:
        """
        Get a summary of the current configuration.

        Returns:
            str: Formatted configuration summary
        """
        summary = [
            "Configuration Summary:",
            f"  Claude Model: {cls.CLAUDE_MODEL}",
            f"  Claude Timeout: {cls.CLAUDE_TIMEOUT_SECONDS}s",
            f"  APIs Config: {cls.APIS_CONFIG_FILE}",
            f"  Prompts Config: {cls.PROMPTS_CONFIG_FILE}",
            f"  Results Directory: {cls.RESULTS_DIR}",
            f"  Debug Mode: {cls.DEBUG_MODE}",
        ]
        return "\n".join(summary)

    @classmethod
    def print_config(cls) -> None:
        """Print the current configuration to stdout."""
        print(cls.get_summary())

