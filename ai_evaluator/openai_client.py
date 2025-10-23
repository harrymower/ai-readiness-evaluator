"""OpenAI client - handles communication with OpenAI API for evaluation analysis."""

import os
from typing import Dict, Any, Optional
from ai_evaluator.config import Config


class OpenAIClientError(Exception):
    """Custom exception for OpenAI client errors."""
    pass


class OpenAIClient:
    """Client for interacting with OpenAI API for evaluation analysis."""

    def __init__(self):
        """Initialize the OpenAI client."""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise OpenAIClientError("OPENAI_API_KEY not found in environment variables")
        
        self.model = "gpt-4o"  # Using GPT-4o (latest available)
        self.debug = Config.DEBUG_MODE
        
        # Import openai here to avoid import errors if not installed
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise OpenAIClientError(
                "OpenAI library not installed. Install with: pip install openai"
            )

    def analyze_test_results(
        self,
        api_name: str,
        round_name: str,
        test_results: Dict[str, Any],
        evaluation_score: int
    ) -> str:
        """
        Use OpenAI to analyze test results and generate detailed evaluation reasoning.

        Args:
            api_name: Name of the API being evaluated
            round_name: Name of the round
            test_results: Test execution results
            evaluation_score: The score assigned to this evaluation

        Returns:
            str: Detailed analysis from OpenAI

        Raises:
            OpenAIClientError: If API call fails
        """
        try:
            # Build the analysis prompt
            prompt = self._build_analysis_prompt(
                api_name, round_name, test_results, evaluation_score
            )

            if self.debug:
                print(f"[DEBUG] Sending analysis request to OpenAI...")
                print(f"[DEBUG] Model: {self.model}")

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert code reviewer and testing analyst. Provide detailed, constructive analysis of test results and code quality."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1500
            )

            analysis = response.choices[0].message.content
            
            if self.debug:
                print(f"[DEBUG] Received analysis from OpenAI")

            return analysis

        except Exception as e:
            raise OpenAIClientError(f"Failed to analyze test results: {e}")

    def _build_analysis_prompt(
        self,
        api_name: str,
        round_name: str,
        test_results: Dict[str, Any],
        evaluation_score: int
    ) -> str:
        """
        Build a detailed prompt for OpenAI to analyze test results.

        Args:
            api_name: Name of the API
            round_name: Name of the round
            test_results: Test execution results
            evaluation_score: The evaluation score

        Returns:
            str: Formatted prompt for OpenAI
        """
        passed = test_results.get('passed', 0)
        failed = test_results.get('failed', 0)
        errors = test_results.get('errors', 0)
        total = test_results.get('total', 0)
        details = test_results.get('details', [])

        # Build test details section
        test_details_text = ""
        if details:
            passed_tests = [t for t in details if t.get('status') == 'PASSED']
            failed_tests = [t for t in details if t.get('status') == 'FAILED']
            error_tests = [t for t in details if t.get('status') == 'ERROR']

            if passed_tests:
                test_details_text += "\nPassed Tests:\n"
                for test in passed_tests:
                    test_name = test.get('name', 'Unknown').split('::')[-1]
                    test_details_text += f"  - {test_name}\n"

            if failed_tests:
                test_details_text += "\nFailed Tests:\n"
                for test in failed_tests:
                    test_name = test.get('name', 'Unknown').split('::')[-1]
                    reason = test.get('reason', 'No reason provided')
                    test_details_text += f"  - {test_name}: {reason}\n"

            if error_tests:
                test_details_text += "\nError Tests:\n"
                for test in error_tests:
                    test_name = test.get('name', 'Unknown').split('::')[-1]
                    reason = test.get('reason', 'No reason provided')
                    test_details_text += f"  - {test_name}: {reason}\n"

        prompt = f"""Analyze the following test results for a Python CLI tool and provide a detailed evaluation report.

API: {api_name}
Round: {round_name}
Evaluation Score: {evaluation_score}/100

Test Results Summary:
- Passed: {passed}/{total}
- Failed: {failed}/{total}
- Errors: {errors}/{total}
- Pass Rate: {(passed/total*100):.1f}%
{test_details_text}

Please provide:
1. A detailed analysis of why the code received this score
2. Specific issues identified in the failed/error tests
3. What the code does well
4. Key areas for improvement
5. Recommendations for fixing the issues
6. Overall assessment of code quality and functionality

Format your response in clear sections with headers."""

        return prompt

