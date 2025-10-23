"""Tests for the test_runner module."""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from ai_evaluator.test_runner import TestRunner, TestRunnerError
from ai_evaluator.config import Config


class TestTestRunnerInitialization:
    """Test cases for TestRunner initialization."""

    def test_runner_initialization(self):
        """Test that runner initializes correctly."""
        runner = TestRunner("test_file.py")
        assert runner.test_file_path == "test_file.py"
        assert runner.timeout == Config.CLAUDE_TIMEOUT_SECONDS
        assert runner.debug == Config.DEBUG_MODE

    def test_runner_custom_timeout(self):
        """Test runner with custom timeout."""
        runner = TestRunner("test_file.py", timeout=60)
        assert runner.timeout == 60

    def test_runner_uses_config_debug(self):
        """Test that runner uses config debug mode."""
        runner = TestRunner("test_file.py")
        assert runner.debug == Config.DEBUG_MODE


class TestRunTests:
    """Test cases for running tests."""

    def test_run_tests_file_not_found(self):
        """Test error when test file doesn't exist."""
        runner = TestRunner("nonexistent_file.py")
        with pytest.raises(TestRunnerError) as exc_info:
            runner.run_tests()

        assert "Test file not found" in str(exc_info.value)

    @patch('subprocess.run')
    def test_run_tests_success(self, mock_run):
        """Test successful test execution."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test_example(): pass")
            test_file = f.name

        try:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "test_file.py::test_example PASSED\n\n1 passed in 0.01s"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            runner = TestRunner(test_file)
            results = runner.run_tests()

            assert results['success'] is True
            assert results['passed'] == 1
            assert results['failed'] == 0

        finally:
            os.unlink(test_file)

    @patch('subprocess.run')
    def test_run_tests_with_failures(self, mock_run):
        """Test test execution with failures."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test_example(): pass")
            test_file = f.name

        try:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = "test_file.py::test_example FAILED\n\n1 failed in 0.01s"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            runner = TestRunner(test_file)
            results = runner.run_tests()

            assert results['success'] is False
            assert results['failed'] == 1

        finally:
            os.unlink(test_file)

    @patch('subprocess.run')
    def test_run_tests_timeout(self, mock_run):
        """Test timeout handling."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test_example(): pass")
            test_file = f.name

        try:
            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired("pytest", 180)

            runner = TestRunner(test_file)
            with pytest.raises(TestRunnerError) as exc_info:
                runner.run_tests()

            assert "timed out" in str(exc_info.value).lower()

        finally:
            os.unlink(test_file)

    @patch('subprocess.run')
    def test_run_tests_pytest_not_found(self, mock_run):
        """Test error when pytest is not found."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test_example(): pass")
            test_file = f.name

        try:
            mock_run.side_effect = FileNotFoundError()

            runner = TestRunner(test_file)
            with pytest.raises(TestRunnerError) as exc_info:
                runner.run_tests()

            assert "pytest not found" in str(exc_info.value).lower()

        finally:
            os.unlink(test_file)


class TestExtractCount:
    """Test cases for extracting test counts."""

    def test_extract_passed_count(self):
        """Test extracting passed count."""
        output = "test_file.py::test_example PASSED\n\n5 passed in 0.01s"
        runner = TestRunner("test_file.py")
        count = runner._extract_count(output, 'passed')
        assert count == 5

    def test_extract_failed_count(self):
        """Test extracting failed count."""
        output = "test_file.py::test_example FAILED\n\n2 failed in 0.01s"
        runner = TestRunner("test_file.py")
        count = runner._extract_count(output, 'failed')
        assert count == 2

    def test_extract_error_count(self):
        """Test extracting error count."""
        output = "test_file.py::test_example ERROR\n\n1 error in 0.01s"
        runner = TestRunner("test_file.py")
        count = runner._extract_count(output, 'error')
        assert count == 1

    def test_extract_count_not_found(self):
        """Test when count is not found."""
        output = "No tests found"
        runner = TestRunner("test_file.py")
        count = runner._extract_count(output, 'passed')
        assert count == 0


class TestExtractTestDetails:
    """Test cases for extracting test details."""

    def test_extract_single_test_passed(self):
        """Test extracting single passed test."""
        output = "test_file.py::test_example PASSED"
        runner = TestRunner("test_file.py")
        details = runner._extract_test_details(output)

        assert len(details) == 1
        assert details[0]['name'] == "test_file.py::test_example"
        assert details[0]['status'] == "PASSED"

    def test_extract_multiple_tests(self):
        """Test extracting multiple tests."""
        output = "test_file.py::test_one PASSED\ntest_file.py::test_two FAILED\ntest_file.py::test_three PASSED"
        runner = TestRunner("test_file.py")
        details = runner._extract_test_details(output)

        assert len(details) == 3
        assert details[0]['status'] == "PASSED"
        assert details[1]['status'] == "FAILED"
        assert details[2]['status'] == "PASSED"

    def test_extract_test_with_error(self):
        """Test extracting test with error."""
        output = "test_file.py::test_example ERROR"
        runner = TestRunner("test_file.py")
        details = runner._extract_test_details(output)

        assert len(details) == 1
        assert details[0]['status'] == "ERROR"

    def test_extract_no_tests(self):
        """Test when no tests are found."""
        output = "No tests found"
        runner = TestRunner("test_file.py")
        details = runner._extract_test_details(output)

        assert len(details) == 0


class TestParseOutput:
    """Test cases for parsing pytest output."""

    def test_parse_output_all_passed(self):
        """Test parsing output with all tests passed."""
        stdout = "test_file.py::test_one PASSED\ntest_file.py::test_two PASSED\n\n2 passed in 0.01s"
        runner = TestRunner("test_file.py")
        results = runner._parse_pytest_output(stdout, "", 0)

        assert results['passed'] == 2
        assert results['failed'] == 0
        assert results['errors'] == 0
        assert results['total'] == 2
        assert results['success'] is True

    def test_parse_output_with_failures(self):
        """Test parsing output with failures."""
        stdout = "test_file.py::test_one PASSED\ntest_file.py::test_two FAILED\n\n1 passed, 1 failed in 0.01s"
        runner = TestRunner("test_file.py")
        results = runner._parse_pytest_output(stdout, "", 1)

        assert results['passed'] == 1
        assert results['failed'] == 1
        assert results['success'] is False

    def test_parse_output_with_errors(self):
        """Test parsing output with errors."""
        stdout = "test_file.py::test_one ERROR\n\n1 error in 0.01s"
        runner = TestRunner("test_file.py")
        results = runner._parse_pytest_output(stdout, "", 1)

        assert results['errors'] == 1
        assert results['success'] is False


class TestInstallDependencies:
    """Test cases for installing dependencies."""

    def test_install_dependencies_file_not_found(self):
        """Test when requirements file doesn't exist."""
        runner = TestRunner("test_file.py")
        result = runner.install_dependencies("nonexistent_requirements.txt")
        assert result is False

    @patch('subprocess.run')
    def test_install_dependencies_success(self, mock_run):
        """Test successful dependency installation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("pytest==7.0.0\n")
            req_file = f.name

        try:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            runner = TestRunner("test_file.py")
            result = runner.install_dependencies(req_file)

            assert result is True

        finally:
            os.unlink(req_file)

    @patch('subprocess.run')
    def test_install_dependencies_failure(self, mock_run):
        """Test failed dependency installation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("nonexistent-package==1.0.0\n")
            req_file = f.name

        try:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Package not found"
            mock_run.return_value = mock_result

            runner = TestRunner("test_file.py")
            result = runner.install_dependencies(req_file)

            assert result is False

        finally:
            os.unlink(req_file)


class TestGetCoverageSummary:
    """Test cases for coverage summary generation."""

    def test_summary_all_passed(self):
        """Test summary when all tests passed."""
        results = {
            'passed': 5,
            'failed': 0,
            'errors': 0,
            'total': 5,
            'success': True
        }
        runner = TestRunner("test_file.py")
        summary = runner.get_test_coverage_summary(results)

        assert "5/5 tests passed" in summary
        assert "100.0%" in summary
        assert "✓" in summary

    def test_summary_with_failures(self):
        """Test summary with failures."""
        results = {
            'passed': 3,
            'failed': 2,
            'errors': 0,
            'total': 5,
            'success': False
        }
        runner = TestRunner("test_file.py")
        summary = runner.get_test_coverage_summary(results)

        assert "3/5 tests passed" in summary
        assert "60.0%" in summary
        assert "2 failed" in summary
        assert "✗" in summary

    def test_summary_with_errors(self):
        """Test summary with errors."""
        results = {
            'passed': 3,
            'failed': 1,
            'errors': 1,
            'total': 5,
            'success': False
        }
        runner = TestRunner("test_file.py")
        summary = runner.get_test_coverage_summary(results)

        assert "3/5 tests passed" in summary
        assert "1 failed" in summary
        assert "1 errors" in summary

    def test_summary_no_tests(self):
        """Test summary when no tests found."""
        results = {
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'total': 0,
            'success': False
        }
        runner = TestRunner("test_file.py")
        summary = runner.get_test_coverage_summary(results)

        assert "No tests found" in summary

