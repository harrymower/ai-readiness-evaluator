"""Tests for the config module."""

import os
import pytest
import tempfile
from ai_evaluator.config import Config, ConfigError


class TestConfigLoading:
    """Test cases for configuration loading."""

    def test_config_defaults(self):
        """Test that default configuration values are loaded."""
        assert Config.CLAUDE_TIMEOUT_SECONDS == 180
        assert Config.CLAUDE_MODEL == "claude-3-5-sonnet-20241022"
        assert Config.APIS_CONFIG_FILE == "config/apis.txt"
        assert Config.PROMPTS_CONFIG_FILE == "config/prompts.txt"
        assert Config.RESULTS_DIR == "results"
        assert Config.DEBUG_MODE is False

    def test_config_debug_mode_parsing(self):
        """Test that DEBUG_MODE is correctly parsed from environment."""
        # This test verifies the boolean parsing logic
        # The actual value depends on .env file
        assert isinstance(Config.DEBUG_MODE, bool)

    def test_config_timeout_is_integer(self):
        """Test that CLAUDE_TIMEOUT_SECONDS is an integer."""
        assert isinstance(Config.CLAUDE_TIMEOUT_SECONDS, int)
        assert Config.CLAUDE_TIMEOUT_SECONDS > 0


class TestConfigValidation:
    """Test cases for configuration validation."""

    def test_validate_success(self):
        """Test that validation succeeds with valid configuration."""
        # This should not raise an exception
        try:
            Config.validate()
        except ConfigError as e:
            pytest.fail(f"Config validation failed unexpectedly: {e}")

    def test_validate_creates_results_directory(self):
        """Test that validation creates the results directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = os.path.join(tmpdir, "test_results")
            assert not os.path.exists(results_dir)

            # Temporarily override RESULTS_DIR
            original_results_dir = Config.RESULTS_DIR
            Config.RESULTS_DIR = results_dir

            try:
                Config.validate()
                assert os.path.exists(results_dir)
            finally:
                Config.RESULTS_DIR = original_results_dir

    def test_validate_missing_apis_file(self):
        """Test that validation fails when APIs config file is missing."""
        original_apis_file = Config.APIS_CONFIG_FILE
        Config.APIS_CONFIG_FILE = "/nonexistent/path/apis.txt"

        try:
            with pytest.raises(ConfigError) as exc_info:
                Config.validate()
            assert "APIs config file not found" in str(exc_info.value)
        finally:
            Config.APIS_CONFIG_FILE = original_apis_file

    def test_validate_missing_prompts_file(self):
        """Test that validation fails when prompts config file is missing."""
        original_prompts_file = Config.PROMPTS_CONFIG_FILE
        Config.PROMPTS_CONFIG_FILE = "/nonexistent/path/prompts.txt"

        try:
            with pytest.raises(ConfigError) as exc_info:
                Config.validate()
            assert "Prompts config file not found" in str(exc_info.value)
        finally:
            Config.PROMPTS_CONFIG_FILE = original_prompts_file

    def test_validate_invalid_timeout(self):
        """Test that validation fails with invalid timeout."""
        original_timeout = Config.CLAUDE_TIMEOUT_SECONDS
        Config.CLAUDE_TIMEOUT_SECONDS = -1

        try:
            with pytest.raises(ConfigError) as exc_info:
                Config.validate()
            assert "must be positive" in str(exc_info.value)
        finally:
            Config.CLAUDE_TIMEOUT_SECONDS = original_timeout

    def test_validate_empty_model(self):
        """Test that validation fails with empty model."""
        original_model = Config.CLAUDE_MODEL
        Config.CLAUDE_MODEL = ""

        try:
            with pytest.raises(ConfigError) as exc_info:
                Config.validate()
            assert "cannot be empty" in str(exc_info.value)
        finally:
            Config.CLAUDE_MODEL = original_model


class TestConfigSummary:
    """Test cases for configuration summary."""

    def test_get_summary(self):
        """Test that get_summary returns a formatted string."""
        summary = Config.get_summary()
        assert isinstance(summary, str)
        assert "Configuration Summary:" in summary
        assert "Claude Model:" in summary
        assert "Claude Timeout:" in summary
        assert "APIs Config:" in summary
        assert "Prompts Config:" in summary
        assert "Results Directory:" in summary
        assert "Debug Mode:" in summary

    def test_get_summary_contains_values(self):
        """Test that get_summary contains actual configuration values."""
        summary = Config.get_summary()
        assert Config.CLAUDE_MODEL in summary
        assert str(Config.CLAUDE_TIMEOUT_SECONDS) in summary
        assert Config.APIS_CONFIG_FILE in summary
        assert Config.PROMPTS_CONFIG_FILE in summary
        assert Config.RESULTS_DIR in summary

    def test_print_config(self, capsys):
        """Test that print_config outputs to stdout."""
        Config.print_config()
        captured = capsys.readouterr()
        assert "Configuration Summary:" in captured.out
        assert Config.CLAUDE_MODEL in captured.out

