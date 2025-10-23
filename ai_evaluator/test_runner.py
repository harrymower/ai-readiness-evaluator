"""Test runner - executes pytest and parses results."""

import subprocess
import os
from typing import Dict, Any, List, Optional
from ai_evaluator.config import Config


class TestRunnerError(Exception):
    """Custom exception for test runner errors."""
    pass


class TestRunner:
    """Runs pytest on generated tests and parses results."""

    def __init__(self, test_file_path: str, timeout: Optional[int] = None):
        """
        Initialize the test runner.

        Args:
            test_file_path: Path to the test file to run
            timeout: Timeout in seconds for pytest execution (defaults to Config.CLAUDE_TIMEOUT_SECONDS)
        """
        self.test_file_path = test_file_path
        self.timeout = timeout or Config.CLAUDE_TIMEOUT_SECONDS
        self.debug = Config.DEBUG_MODE

    def run_tests(self) -> Dict[str, Any]:
        """
        Run pytest on the test file and return results.

        Returns:
            dict: Structured test results with:
                - passed: Number of passed tests
                - failed: Number of failed tests
                - errors: Number of errors
                - total: Total number of tests
                - success: Whether all tests passed
                - details: List of individual test results
                - output: Raw pytest output

        Raises:
            TestRunnerError: If pytest execution fails
        """
        if not os.path.exists(self.test_file_path):
            raise TestRunnerError(f"Test file not found: {self.test_file_path}")

        try:
            # Run pytest with JSON output
            cmd = [
                "python", "-m", "pytest",
                self.test_file_path,
                "--json-report",
                "--json-report-file=/dev/null",  # Suppress file output
                "-v",
                "--tb=short"
            ]

            if self.debug:
                print(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=os.path.dirname(self.test_file_path) or "."
            )

            # Parse the output
            return self._parse_pytest_output(result.stdout, result.stderr, result.returncode)

        except subprocess.TimeoutExpired:
            raise TestRunnerError(f"Pytest execution timed out after {self.timeout} seconds")
        except FileNotFoundError:
            raise TestRunnerError("pytest not found. Please install it with: pip install pytest")
        except Exception as e:
            raise TestRunnerError(f"Failed to run pytest: {e}")

    def _parse_pytest_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse pytest output and return structured results.

        Args:
            stdout: Standard output from pytest
            stderr: Standard error from pytest
            returncode: Return code from pytest

        Returns:
            dict: Structured test results
        """
        # Try to parse pytest output
        try:
            # Combine stdout and stderr for parsing (pytest might output to either)
            combined_output = stdout + "\n" + stderr

            # Extract test counts from pytest output
            # Format: "X passed, Y failed, Z errors in 0.12s"
            passed = self._extract_count(combined_output, 'passed')
            failed = self._extract_count(combined_output, 'failed')
            errors = self._extract_count(combined_output, 'error')

            total = passed + failed + errors
            success = returncode == 0 and failed == 0 and errors == 0

            if self.debug:
                print(f"[DEBUG] Test parsing: passed={passed}, failed={failed}, errors={errors}, total={total}")
                print(f"[DEBUG] Return code: {returncode}")

            return {
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'total': total,
                'success': success,
                'returncode': returncode,
                'output': stdout,
                'error_output': stderr,
                'details': self._extract_test_details(stdout)
            }

        except Exception as e:
            if self.debug:
                print(f"Error parsing pytest output: {e}")

            # Fallback: return basic results based on return code
            return {
                'passed': 0,
                'failed': 0,
                'errors': 0,
                'total': 0,
                'success': returncode == 0,
                'returncode': returncode,
                'output': stdout,
                'error_output': stderr,
                'details': [],
                'parse_error': str(e)
            }

    def _extract_count(self, output: str, keyword: str) -> int:
        """
        Extract count of tests from pytest output.

        Args:
            output: Pytest output text
            keyword: Keyword to search for (passed, failed, error)

        Returns:
            int: Count of tests matching keyword
        """
        import re

        # Look for patterns like "5 passed", "2 failed", "1 error"
        pattern = rf'(\d+)\s+{keyword}'
        matches = re.findall(pattern, output)

        if matches:
            return int(matches[-1])  # Return the last match (usually in summary)

        return 0

    def _extract_test_details(self, output: str) -> List[Dict[str, str]]:
        """
        Extract individual test results from pytest output.

        Args:
            output: Pytest output text

        Returns:
            list: List of test result dictionaries with name, status, and failure reason
        """
        details = []
        lines = output.split('\n')

        for line in lines:
            # Look for test result lines
            # Format: "test_file.py::test_name PASSED" or "test_file.py::test_name FAILED"
            if '::' in line and (' PASSED' in line or ' FAILED' in line or ' ERROR' in line):
                # Extract test name and status
                test_full_name = line.split()[0] if line.split() else ''
                test_name = test_full_name.split('::')[-1] if '::' in test_full_name else test_full_name

                # Determine status
                status = 'UNKNOWN'
                if ' PASSED' in line:
                    status = 'PASSED'
                elif ' FAILED' in line:
                    status = 'FAILED'
                elif ' ERROR' in line:
                    status = 'ERROR'

                test_detail = {
                    'name': test_name,
                    'status': status,
                    'reason': ''
                }

                # Extract failure reason if test failed
                if status in ['FAILED', 'ERROR']:
                    reason = self._extract_failure_reason(output, test_name)
                    if reason:
                        test_detail['reason'] = reason

                details.append(test_detail)

        return details

    def _extract_failure_reason(self, output: str, test_name: str) -> str:
        """
        Extract the failure reason for a failed test.

        Args:
            output: Full pytest output
            test_name: Name of the test that failed

        Returns:
            str: Failure reason or empty string if not found
        """
        lines = output.split('\n')

        # Look for the FAILURES section which contains detailed error info
        failures_section_start = -1
        for i, line in enumerate(lines):
            if '== FAILURES ==' in line or '=== FAILURES ===' in line:
                failures_section_start = i
                break

        if failures_section_start == -1:
            return ''

        # Find the specific test failure in the FAILURES section
        reason_lines = []
        in_test_failure = False

        for i in range(failures_section_start, len(lines)):
            line = lines[i]

            # Check if this is the start of our test's failure details
            # Look for lines like "______ test_name ______"
            if test_name in line and ('_' in line or 'test_' in line):
                in_test_failure = True
                continue

            # If we're in the test failure section, collect error details
            if in_test_failure:
                # Stop at the next test failure or summary section
                if line.startswith('_') or line.startswith('=') or (line.strip() and 'test_' in line and '::' in line):
                    break

                # Capture error lines (those starting with E or containing assertion info)
                stripped = line.strip()
                if stripped.startswith('E '):
                    # Remove the 'E ' prefix and add to reasons
                    reason_lines.append(stripped[2:])
                elif stripped and not stripped.startswith('-') and stripped:
                    # Also capture context lines
                    if any(keyword in stripped for keyword in ['assert', 'Error', 'Exception', 'Failed', 'in ']):
                        reason_lines.append(stripped)

                # Limit to a reasonable number of lines
                if len(reason_lines) >= 5:
                    break

        return ' | '.join(reason_lines) if reason_lines else ''

    def install_dependencies(self, requirements_file: str = "requirements.txt") -> bool:
        """
        Install dependencies from a requirements file.

        Args:
            requirements_file: Path to requirements.txt file

        Returns:
            bool: True if installation succeeded, False otherwise
        """
        if not os.path.exists(requirements_file):
            if self.debug:
                print(f"Requirements file not found: {requirements_file}")
            return False

        try:
            if self.debug:
                print(f"Installing dependencies from {requirements_file}")

            result = subprocess.run(
                ["pip", "install", "-r", requirements_file],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for pip install
            )

            if result.returncode == 0:
                if self.debug:
                    print("Dependencies installed successfully")
                return True
            else:
                if self.debug:
                    print(f"Dependency installation failed: {result.stderr}")
                return False

        except Exception as e:
            if self.debug:
                print(f"Error installing dependencies: {e}")
            return False

    def get_test_coverage_summary(self, results: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of test results.

        Args:
            results: Test results dictionary from run_tests()

        Returns:
            str: Human-readable summary
        """
        passed = results.get('passed', 0)
        failed = results.get('failed', 0)
        errors = results.get('errors', 0)
        total = results.get('total', 0)
        success = results.get('success', False)

        if total == 0:
            return "No tests found"

        pass_rate = (passed / total * 100) if total > 0 else 0

        summary = f"{passed}/{total} tests passed ({pass_rate:.1f}%)"

        if failed > 0:
            summary += f", {failed} failed"

        if errors > 0:
            summary += f", {errors} errors"

        if success:
            summary += " ✓"
        else:
            summary += " ✗"

        return summary

