"""Main entry point - orchestrates the entire evaluation workflow."""

import sys
import os
import tempfile
from datetime import datetime
from ai_evaluator.config import Config, ConfigError
from ai_evaluator.utils import (
    parse_apis_config, parse_prompts_config,
    write_file, FileError, ParseError
)
from ai_evaluator.claude_client import ClaudeClient, ClaudeClientError
from ai_evaluator.test_runner import TestRunner, TestRunnerError
from ai_evaluator.evaluator import Evaluator, EvaluatorError
from ai_evaluator.report_generator import ReportGenerator, ReportGeneratorError


def _get_next_test_number(results_dir: str) -> str:
    """
    Find the next available test number (test-001, test-002, etc.).

    Args:
        results_dir: Path to the results directory

    Returns:
        str: Next test number in format 'test-###'
    """
    os.makedirs(results_dir, exist_ok=True)

    # Find all existing test directories
    existing_tests = []
    for item in os.listdir(results_dir):
        if item.startswith('test-') and os.path.isdir(os.path.join(results_dir, item)):
            try:
                num = int(item.split('-')[1])
                existing_tests.append(num)
            except (ValueError, IndexError):
                pass

    # Get next number
    next_num = max(existing_tests) + 1 if existing_tests else 1
    return f"test-{next_num:03d}"


def _api_name_to_folder(api_name: str) -> str:
    """
    Convert API name to folder name (e.g., OPEN_METEO_WEATHER -> open-meteo-weather).

    Args:
        api_name: API name from config

    Returns:
        str: Folder-friendly name
    """
    return api_name.lower().replace('_', '-')


def _round_name_to_folder(round_name: str) -> str:
    """
    Convert round name to folder name (e.g., ROUND_1_CURL_ONLY -> round-1-curl-only).

    Args:
        round_name: Round name from config

    Returns:
        str: Folder-friendly name
    """
    return round_name.lower().replace('_', '-')


class EvaluatorOrchestrator:
    """Orchestrates the AI Readiness Evaluation workflow."""

    def __init__(self, rounds_filter=None):
        """
        Initialize the orchestrator.

        Args:
            rounds_filter: Optional list of round names to run (e.g., ['ROUND_1_CURL_ONLY'])
        """
        self.config = Config
        self.apis = {}
        self.prompts = {}
        self.results = {}
        self.rounds_filter = rounds_filter
        self.test_dir = None  # Will be set during run
        self.round_transcripts = {}  # Track transcripts for each round

    def run(self) -> int:
        """
        Run the complete evaluation workflow.

        Returns:
            int: Exit code (0 for success, 1 for failure)
        """
        try:
            self._validate_configuration()
            self._load_configurations()
            self._create_test_directory()
            self._print_startup_info()
            self._run_evaluations()
            self._generate_reports()
            self._print_completion_info()
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            if self.config.DEBUG_MODE:
                import traceback
                traceback.print_exc()
            return 1

    def _validate_configuration(self) -> None:
        """Validate that all required configuration is present."""
        print("Validating configuration...")
        try:
            self.config.validate()
            print("✓ Configuration validated successfully")
        except ConfigError as e:
            raise ConfigError(f"Configuration validation failed: {e}")

    def _load_configurations(self) -> None:
        """Load APIs and prompts configurations."""
        print("\nLoading configurations...")

        try:
            # Load APIs configuration
            print(f"  Loading APIs from: {self.config.APIS_CONFIG_FILE}")
            self.apis = parse_apis_config(self.config.APIS_CONFIG_FILE)
            print(f"  ✓ Loaded {len(self.apis)} API(s)")

            # Load prompts configuration
            print(f"  Loading prompts from: {self.config.PROMPTS_CONFIG_FILE}")
            self.prompts = parse_prompts_config(self.config.PROMPTS_CONFIG_FILE)
            print(f"  ✓ Loaded {len(self.prompts)} prompt template(s)")

        except (FileError, ParseError) as e:
            raise Exception(f"Failed to load configurations: {e}")

    def _create_test_directory(self) -> None:
        """Create a new numbered test directory to prevent file overwrites."""
        os.makedirs(self.config.RESULTS_DIR, exist_ok=True)
        self.test_dir = os.path.join(
            self.config.RESULTS_DIR,
            _get_next_test_number(self.config.RESULTS_DIR)
        )
        os.makedirs(self.test_dir, exist_ok=True)
        if self.config.DEBUG_MODE:
            print(f"[DEBUG] Created test directory: {self.test_dir}")

    def _print_startup_info(self) -> None:
        """Print startup information."""
        print("\n" + "="*70)
        print("AI READINESS EVALUATOR - STARTUP INFORMATION")
        print("="*70)
        self.config.print_config()
        print(f"\nAPIs to evaluate: {', '.join(self.apis.keys())}")
        print(f"Rounds to execute: {', '.join(self.prompts.keys())}")
        print("="*70 + "\n")

    def _run_evaluations(self) -> None:
        """Run evaluations for each API and round."""
        print("Starting evaluations...\n")

        evaluator = Evaluator()
        report_generator = ReportGenerator(self.test_dir)

        for round_name, prompt_template in self.prompts.items():
            # Skip rounds not in filter if filter is specified
            if self.rounds_filter and round_name not in self.rounds_filter:
                continue

            # Initialize round directory
            round_folder = _round_name_to_folder(round_name)
            round_dir = os.path.join(self.test_dir, round_folder)
            os.makedirs(round_dir, exist_ok=True)

            for api_name, api_config in self.apis.items():
                print(f"Evaluating API: {api_name}")
                print(f"  Description: {api_config.get('description', 'N/A')}")
                curl_cmd = api_config.get('curl_command', 'N/A')
                print(f"  Curl command: {curl_cmd[:60]}...")

                # Initialize results for this API
                if api_name not in self.results:
                    self.results[api_name] = {}

                # Create API-specific folder
                api_folder = _api_name_to_folder(api_name)
                api_dir = os.path.join(round_dir, api_folder)
                os.makedirs(api_dir, exist_ok=True)

                print(f"  → {round_name}")

                # Initialize ClaudeClient with API-specific directory
                claude_client = ClaudeClient(working_dir=api_dir)

                # Initialize transcripts for working and testing phases
                working_transcript = []
                testing_transcript = []
                working_transcript.append(f"# Working Phase Transcript - {api_name} ({round_name})\n\n")
                working_transcript.append(f"**Generated at**: {datetime.now().isoformat()}\n\n")
                testing_transcript.append(f"# Testing Phase Transcript - {api_name} ({round_name})\n\n")
                testing_transcript.append(f"**Generated at**: {datetime.now().isoformat()}\n\n")

                try:
                    # Step 1: Build the prompt with API-specific information
                    prompt = self._build_prompt(
                        prompt_template, api_name, api_config
                    )

                    # Step 2: Send prompt to Claude and get response
                    if self.config.DEBUG_MODE:
                        print(f"    Sending prompt to Claude...")
                        print(f"    [DEBUG] Prompt length: {len(prompt)}")
                        print(f"    [DEBUG] Full prompt:\n{prompt}\n")
                    claude_response = claude_client.send_prompt(prompt)

                    # Add to working phase transcript
                    working_transcript.append(f"## Prompt\n\n```\n{prompt}\n```\n\n")
                    working_transcript.append(f"## Claude Response\n\n```\n{claude_response[:1000]}...\n```\n\n")

                    # Step 3: Extract code and tests from Claude's response
                    code_and_tests = claude_client.parse_response_for_code_and_tests(
                        claude_response
                    )
                    cli_code = code_and_tests.get('code', '')
                    test_code = code_and_tests.get('tests', '')

                    if not cli_code or not test_code:
                        raise ValueError("Claude did not generate both code and tests")

                    # Step 4: Create temporary directory for generated code
                    with tempfile.TemporaryDirectory() as tmpdir:
                        # Write generated code and tests to temp directory
                        cli_path = os.path.join(tmpdir, "cli_tool.py")
                        test_path = os.path.join(tmpdir, "test_cli_tool.py")
                        write_file(cli_path, cli_code)
                        write_file(test_path, test_code)

                        # Step 5: Run tests
                        if self.config.DEBUG_MODE:
                            print(f"    Running tests...")
                        test_runner = TestRunner(test_path)
                        test_results = test_runner.run_tests()

                        # Step 6: Evaluate results
                        if self.config.DEBUG_MODE:
                            print(f"    Evaluating results...")
                        evaluation = evaluator.evaluate(
                            cli_path, test_results
                        )

                        # Step 7: Generate evaluation report in API folder
                        report_path = report_generator.generate_evaluation_report(
                            round_name=round_name,
                            api_name=api_name,
                            evaluation_results=evaluation,
                            output_dir=api_dir,
                            test_results=test_results
                        )

                        # Also save generated code to API folder
                        write_file(os.path.join(api_dir, "cli_tool.py"), cli_code)
                        write_file(os.path.join(api_dir, "test_cli_tool.py"), test_code)

                        # Add test results to testing phase transcript
                        testing_transcript.append(f"## Test Execution\n\n")
                        testing_transcript.append(f"### Test Results Summary\n\n")
                        testing_transcript.append(f"- **Passed**: {test_results.get('passed', 0)}\n")
                        testing_transcript.append(f"- **Failed**: {test_results.get('failed', 0)}\n")
                        testing_transcript.append(f"- **Errors**: {test_results.get('errors', 0)}\n")
                        testing_transcript.append(f"- **Total**: {test_results.get('total', 0)}\n\n")

                        # Add detailed test results
                        test_details = test_results.get('details', [])
                        if test_details:
                            testing_transcript.append(f"### Individual Test Results\n\n")
                            for test in test_details:
                                test_name = test.get('name', 'Unknown').split('::')[-1]
                                status = test.get('status', 'UNKNOWN')
                                reason = test.get('reason', '')

                                if status == 'PASSED':
                                    testing_transcript.append(f"✓ **{test_name}**: PASSED\n")
                                elif status == 'FAILED':
                                    testing_transcript.append(f"✗ **{test_name}**: FAILED\n")
                                    if reason:
                                        testing_transcript.append(f"  - Reason: {reason}\n")
                                elif status == 'ERROR':
                                    testing_transcript.append(f"⚠ **{test_name}**: ERROR\n")
                                    if reason:
                                        testing_transcript.append(f"  - Reason: {reason}\n")
                            testing_transcript.append(f"\n")

                        # Add pytest output for reference
                        pytest_output = test_results.get('output', '')
                        if pytest_output:
                            testing_transcript.append(f"### Pytest Output\n\n")
                            testing_transcript.append(f"```\n{pytest_output[:2000]}\n```\n\n")

                        testing_transcript.append(f"### Evaluation Results\n\n")
                        testing_transcript.append(f"- **Score**: {evaluation.get('score', 0)}/100\n")
                        testing_transcript.append(f"- **Pass Rate**: {evaluation.get('pass_rate', 0):.1f}%\n")
                        testing_transcript.append(f"- **Reasoning**: {evaluation.get('reasoning', 'N/A')}\n\n")

                        # Store results
                        self.results[api_name][round_name] = {
                            "status": "success",
                            "score": evaluation.get('score', 0),
                            "pass_rate": evaluation.get('pass_rate', 0),
                            "report_path": report_path
                        }

                        if self.config.DEBUG_MODE:
                            print(f"    Score: {evaluation.get('score', 0)}/100")

                except (ClaudeClientError, TestRunnerError, EvaluatorError,
                        ReportGeneratorError, ValueError, FileError) as e:
                    error_msg = f"Evaluation failed: {str(e)}"
                    print(f"    ✗ {error_msg}")
                    testing_transcript.append(f"## Error\n\n{error_msg}\n\n")
                    self.results[api_name][round_name] = {
                        "status": "error",
                        "message": error_msg
                    }
                except Exception as e:
                    error_msg = f"Unexpected error: {str(e)}"
                    print(f"    ✗ {error_msg}")
                    testing_transcript.append(f"## Error\n\n{error_msg}\n\n")
                    self.results[api_name][round_name] = {
                        "status": "error",
                        "message": error_msg
                    }
                    if self.config.DEBUG_MODE:
                        import traceback
                        traceback.print_exc()

                # Save working phase transcript
                working_transcript_path = os.path.join(api_dir, "working_transcript.md")
                try:
                    write_file(working_transcript_path, "".join(working_transcript))
                    if self.config.DEBUG_MODE:
                        print(f"[DEBUG] Saved working transcript to: {working_transcript_path}")
                except FileError as e:
                    print(f"Warning: Failed to save working transcript: {e}", file=sys.stderr)

                # Save testing phase transcript
                testing_transcript_path = os.path.join(api_dir, "testing_transcript.md")
                try:
                    write_file(testing_transcript_path, "".join(testing_transcript))
                    if self.config.DEBUG_MODE:
                        print(f"[DEBUG] Saved testing transcript to: {testing_transcript_path}")
                except FileError as e:
                    print(f"Warning: Failed to save testing transcript: {e}", file=sys.stderr)

            print()

    def _build_prompt(self, template: str, api_name: str,
                      api_config: dict) -> str:
        """
        Build a prompt by substituting placeholders in the template.

        Args:
            template: Prompt template with placeholders
            api_name: Name of the API
            api_config: API configuration dictionary

        Returns:
            str: Formatted prompt ready to send to Claude
        """
        prompt = template

        # Replace curl_command placeholder
        curl_command = api_config.get('curl_command', '')
        prompt = prompt.replace('{curl_command}', curl_command)

        # Replace documentation_url placeholder
        doc_url = api_config.get('documentation_url', '')
        prompt = prompt.replace('{documentation_url}', doc_url)

        # Replace postman_collection_url placeholder
        postman_url = api_config.get('postman_collection_url', '')
        prompt = prompt.replace('{postman_collection_url}', postman_url)

        # Replace example_prompt_url placeholder
        example_url = api_config.get('example_prompt_url', '')
        prompt = prompt.replace('{example_prompt_url}', example_url)

        return prompt

    def _generate_reports(self) -> None:
        """Generate evaluation reports."""
        print("Generating reports...\n")

        # Generate markdown comparison report
        comparison_md = self._generate_comparison_report_markdown()

        # Save to test directory
        test_report_path = os.path.join(self.test_dir, "comparison_report.md")
        try:
            write_file(test_report_path, comparison_md)
            print(f"✓ Comparison report saved to: {test_report_path}")
        except FileError as e:
            print(f"Warning: Failed to save comparison report: {e}", file=sys.stderr)

    def _generate_comparison_report_markdown(self) -> str:
        """
        Generate a markdown comparison report.

        Returns:
            str: Markdown formatted comparison report
        """
        lines = []
        lines.append("# AI Readiness Evaluator - Comparison Report\n\n")
        lines.append(f"**Test Run**: {os.path.basename(self.test_dir)}\n")
        lines.append(f"**Generated**: {datetime.now().isoformat()}\n\n")

        # Executive Summary
        lines.append("## Executive Summary\n\n")
        lines.append(f"- **Total APIs Evaluated**: {len(self.apis)}\n")
        lines.append(f"- **Total Rounds**: {len(self.prompts)}\n")
        lines.append(f"- **Test Directory**: {self.test_dir}\n\n")

        # Round Summary
        lines.append("## Round Summary\n\n")
        for round_name in self.prompts.keys():
            lines.append(f"### {round_name}\n\n")

            round_scores = []
            for api_name in self.apis.keys():
                if api_name in self.results and round_name in self.results[api_name]:
                    result = self.results[api_name][round_name]
                    if result.get("status") == "success":
                        score = result.get("score", 0)
                        round_scores.append(score)
                        lines.append(f"- **{api_name}**: {score}/100\n")
                    else:
                        lines.append(f"- **{api_name}**: Error - {result.get('message', 'Unknown error')}\n")

            if round_scores:
                avg_score = sum(round_scores) / len(round_scores)
                lines.append(f"\n**Average Score**: {avg_score:.1f}/100\n\n")
            else:
                lines.append("\n**Average Score**: N/A (no successful evaluations)\n\n")

        # Per-API Breakdown
        lines.append("## Per-API Breakdown\n\n")
        for api_name in self.apis.keys():
            lines.append(f"### {api_name}\n\n")
            if api_name in self.results:
                for round_name in self.prompts.keys():
                    if round_name in self.results[api_name]:
                        result = self.results[api_name][round_name]
                        if result.get("status") == "success":
                            score = result.get("score", 0)
                            pass_rate = result.get("pass_rate", 0)
                            lines.append(f"- **{round_name}**: {score}/100 (Pass Rate: {pass_rate:.1f}%)\n")
                        else:
                            lines.append(f"- **{round_name}**: Error\n")
            lines.append("\n")

        # Analysis
        lines.append("## Analysis\n\n")
        lines.append("### Overview\n\n")

        # Find best and worst rounds
        all_scores = {}
        for round_name in self.prompts.keys():
            round_scores = []
            for api_name in self.apis.keys():
                if api_name in self.results and round_name in self.results[api_name]:
                    result = self.results[api_name][round_name]
                    if result.get("status") == "success":
                        round_scores.append(result.get("score", 0))
            if round_scores:
                all_scores[round_name] = sum(round_scores) / len(round_scores)

        if all_scores:
            best_round = max(all_scores, key=all_scores.get)
            worst_round = min(all_scores, key=all_scores.get)
            lines.append(f"- **Best Performing Round**: {best_round} ({all_scores[best_round]:.1f}/100)\n")
            lines.append(f"- **Worst Performing Round**: {worst_round} ({all_scores[worst_round]:.1f}/100)\n\n")

        lines.append("### Transcript Logs\n\n")
        lines.append("Detailed transcript logs for each API/round combination are available in:\n\n")
        for round_name in self.prompts.keys():
            round_folder = _round_name_to_folder(round_name)
            for api_name in self.apis.keys():
                api_folder = _api_name_to_folder(api_name)
                lines.append(f"- **{api_name} - {round_name}**:\n")
                lines.append(f"  - Working Phase: `{round_folder}/{api_folder}/working_transcript.md`\n")
                lines.append(f"  - Testing Phase: `{round_folder}/{api_folder}/testing_transcript.md`\n")
        lines.append("\n")

        lines.append("### Generated Code\n\n")
        lines.append("Generated CLI tools and tests for each API/round combination are available in:\n\n")
        for round_name in self.prompts.keys():
            round_folder = _round_name_to_folder(round_name)
            for api_name in self.apis.keys():
                api_folder = _api_name_to_folder(api_name)
                lines.append(f"- `{round_folder}/{api_folder}/`\n")
                lines.append(f"  - `cli_tool.py` - Generated CLI tool\n")
                lines.append(f"  - `test_cli_tool.py` - Generated tests\n")
                lines.append(f"  - `evaluation_report.json` - Evaluation results\n")
        lines.append("\n")

        return "".join(lines)

    def _print_completion_info(self) -> None:
        """Print completion information."""
        print("\n" + "="*70)
        print("EVALUATION COMPLETE")
        print("="*70)
        print(f"Results saved to: {self.config.RESULTS_DIR}")
        print(f"Total APIs evaluated: {len(self.apis)}")
        print(f"Total rounds executed: {len(self.prompts)}")
        print("="*70)


def main():
    """Main entry point for the AI Readiness Evaluator."""
    # Parse command-line arguments
    rounds_filter = None
    if len(sys.argv) > 1:
        # Accept rounds as arguments: python -m ai_evaluator.main ROUND_1_CURL_ONLY
        rounds_filter = sys.argv[1:]

    orchestrator = EvaluatorOrchestrator(rounds_filter=rounds_filter)
    exit_code = orchestrator.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

