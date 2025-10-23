"""Evaluator - implements scoring logic and evaluation."""

import os
from typing import Dict, Any, Optional
from ai_evaluator.config import Config


class EvaluatorError(Exception):
    """Custom exception for evaluator errors."""
    pass


class Evaluator:
    """Evaluates generated CLI tools and tests using the scoring system."""

    def __init__(self):
        """Initialize the evaluator."""
        self.debug = Config.DEBUG_MODE

    def evaluate(
        self,
        cli_tool_path: str,
        test_results: Dict[str, Any],
        code_quality_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a generated CLI tool and its tests.

        Uses a gradient scoring system based on:
        - Test pass rate (primary factor)
        - Code quality metrics (secondary factor)
        - Execution success (tertiary factor)

        Args:
            cli_tool_path: Path to the generated CLI tool
            test_results: Test execution results from TestRunner
            code_quality_metrics: Optional code quality metrics

        Returns:
            dict: Evaluation results with:
                - score: 0-100 score
                - pass_rate: Percentage of tests passed
                - success: Whether evaluation was successful
                - reasoning: Explanation of the score
                - details: Detailed evaluation breakdown

        Raises:
            EvaluatorError: If evaluation fails
        """
        try:
            # Verify CLI tool exists
            if not os.path.exists(cli_tool_path):
                raise EvaluatorError(f"CLI tool not found: {cli_tool_path}")

            # Extract test metrics
            passed = test_results.get('passed', 0)
            failed = test_results.get('failed', 0)
            errors = test_results.get('errors', 0)
            total = test_results.get('total', 0)

            # Calculate pass rate
            pass_rate = (passed / total * 100) if total > 0 else 0

            # Calculate score using gradient system
            score = self._calculate_gradient_score(
                pass_rate=pass_rate,
                code_quality_metrics=code_quality_metrics
            )

            # Generate reasoning
            reasoning = self._generate_reasoning(
                score=score,
                pass_rate=pass_rate,
                passed=passed,
                failed=failed,
                errors=errors,
                total=total
            )

            return {
                'score': score,
                'pass_rate': pass_rate,
                'success': score >= 50,  # 50+ is considered successful
                'reasoning': reasoning,
                'details': {
                    'passed': passed,
                    'failed': failed,
                    'errors': errors,
                    'total': total,
                    'code_quality_metrics': code_quality_metrics or {}
                }
            }

        except EvaluatorError:
            raise
        except Exception as e:
            raise EvaluatorError(f"Evaluation failed: {e}")

    def _calculate_gradient_score(
        self,
        pass_rate: float,
        code_quality_metrics: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Calculate score using gradient system.

        Gradient scoring:
        - 0-20%: 0-20 points (no functionality)
        - 20-40%: 20-40 points (partial functionality)
        - 40-60%: 40-60 points (moderate functionality)
        - 60-80%: 60-80 points (good functionality)
        - 80-100%: 80-100 points (excellent functionality)

        Code quality bonus: +0-10 points

        Args:
            pass_rate: Percentage of tests passed (0-100)
            code_quality_metrics: Optional code quality metrics

        Returns:
            int: Score from 0-100
        """
        # Base score from pass rate (0-90 points)
        base_score = int(pass_rate * 0.9)

        # Code quality bonus (0-10 points)
        quality_bonus = self._calculate_quality_bonus(code_quality_metrics)

        # Total score (0-100)
        total_score = min(100, base_score + quality_bonus)

        return total_score

    def _calculate_quality_bonus(self, metrics: Optional[Dict[str, Any]]) -> int:
        """
        Calculate code quality bonus points.

        Factors:
        - Code length (reasonable size)
        - Has error handling
        - Has documentation
        - Follows conventions

        Args:
            metrics: Code quality metrics

        Returns:
            int: Bonus points (0-10)
        """
        if not metrics:
            return 0

        bonus = 0

        # Check code length (not too short, not too long)
        code_length = metrics.get('code_length', 0)
        if 50 <= code_length <= 500:
            bonus += 2

        # Check for error handling
        if metrics.get('has_error_handling', False):
            bonus += 3

        # Check for documentation
        if metrics.get('has_documentation', False):
            bonus += 3

        # Check for following conventions
        if metrics.get('follows_conventions', False):
            bonus += 2

        return min(10, bonus)

    def _generate_reasoning(
        self,
        score: int,
        pass_rate: float,
        passed: int,
        failed: int,
        errors: int,
        total: int
    ) -> str:
        """
        Generate human-readable reasoning for the score.

        Args:
            score: Final score
            pass_rate: Pass rate percentage
            passed: Number of passed tests
            failed: Number of failed tests
            errors: Number of errors
            total: Total number of tests

        Returns:
            str: Reasoning explanation
        """
        if total == 0:
            return "No tests were executed. Unable to evaluate."

        # Build reasoning based on score ranges
        if score >= 80:
            level = "Excellent"
            description = "The generated code demonstrates strong functionality with high test coverage."
        elif score >= 60:
            level = "Good"
            description = "The generated code works well with most tests passing."
        elif score >= 40:
            level = "Moderate"
            description = "The generated code has partial functionality with some test failures."
        elif score >= 20:
            level = "Poor"
            description = "The generated code has limited functionality with many test failures."
        else:
            level = "Failed"
            description = "The generated code does not function properly."

        # Build detailed reasoning
        reasoning = f"{level} ({score}/100): {description}\n"
        reasoning += f"Test Results: {passed}/{total} passed ({pass_rate:.1f}%)"

        if failed > 0:
            reasoning += f", {failed} failed"

        if errors > 0:
            reasoning += f", {errors} errors"

        return reasoning

    def calculate_score(self, test_results: Dict[str, Any]) -> int:
        """
        Calculate score based on test results.

        This is a simplified version that only uses test results.
        For full evaluation, use evaluate() method.

        Args:
            test_results: Test execution results from TestRunner

        Returns:
            int: Score from 0-100
        """
        passed = test_results.get('passed', 0)
        total = test_results.get('total', 0)

        if total == 0:
            return 0

        pass_rate = (passed / total * 100)
        return self._calculate_gradient_score(pass_rate=pass_rate)

    def compare_evaluations(
        self,
        evaluations: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare multiple evaluations and generate comparison metrics.

        Args:
            evaluations: Dictionary of evaluation results keyed by round name

        Returns:
            dict: Comparison metrics including:
                - best_round: Round with highest score
                - worst_round: Round with lowest score
                - average_score: Average score across rounds
                - improvement: Score improvement from first to last round
                - trend: Whether scores are improving or declining
        """
        if not evaluations:
            raise EvaluatorError("No evaluations to compare")

        scores = [eval_result['score'] for eval_result in evaluations.values()]

        best_round = max(evaluations.items(), key=lambda x: x[1]['score'])
        worst_round = min(evaluations.items(), key=lambda x: x[1]['score'])

        average_score = sum(scores) / len(scores)

        # Calculate improvement
        first_score = scores[0]
        last_score = scores[-1]
        improvement = last_score - first_score

        # Determine trend
        if len(scores) >= 2:
            if improvement > 0:
                trend = "improving"
            elif improvement < 0:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            'best_round': best_round[0],
            'best_score': best_round[1]['score'],
            'worst_round': worst_round[0],
            'worst_score': worst_round[1]['score'],
            'average_score': average_score,
            'improvement': improvement,
            'trend': trend,
            'all_scores': {name: eval_result['score'] for name, eval_result in evaluations.items()}
        }

    def get_score_interpretation(self, score: int) -> str:
        """
        Get human-readable interpretation of a score.

        Args:
            score: Score from 0-100

        Returns:
            str: Interpretation of the score
        """
        if score >= 80:
            return "Excellent - Production ready"
        elif score >= 60:
            return "Good - Ready with minor fixes"
        elif score >= 40:
            return "Moderate - Needs significant work"
        elif score >= 20:
            return "Poor - Major issues"
        else:
            return "Failed - Does not work"

