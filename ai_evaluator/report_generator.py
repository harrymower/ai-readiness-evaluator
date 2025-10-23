"""Report generator - generates evaluation and comparison reports."""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from ai_evaluator.utils import write_json
from ai_evaluator.config import Config
from ai_evaluator.openai_client import OpenAIClient, OpenAIClientError


class ReportGeneratorError(Exception):
    """Custom exception for report generator errors."""
    pass


class ReportGenerator:
    """Generates evaluation reports and comparison reports."""

    def __init__(self, results_dir: str):
        """Initialize the report generator."""
        self.results_dir = results_dir
        self.debug = Config.DEBUG_MODE
        self._ensure_results_dir()

    def _ensure_results_dir(self) -> None:
        """Ensure results directory exists."""
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir, exist_ok=True)

    def generate_evaluation_report(
        self,
        round_name: str,
        api_name: str,
        evaluation_results: Dict[str, Any],
        output_dir: Optional[str] = None,
        test_results: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a markdown evaluation report for a single round/API combination.

        Args:
            round_name: Name of the round (e.g., "ROUND_1_CURL_ONLY")
            api_name: Name of the API being evaluated
            evaluation_results: Evaluation results from Evaluator
            output_dir: Optional custom output directory (defaults to self.results_dir)
            test_results: Optional test results for detailed analysis

        Returns:
            str: Path to the generated markdown report file

        Raises:
            ReportGeneratorError: If report generation fails
        """
        try:
            # Use provided output_dir or default to results_dir
            target_dir = output_dir if output_dir else self.results_dir
            os.makedirs(target_dir, exist_ok=True)

            # Generate markdown report only (no JSON)
            md_filename = f"evaluation_report.md"
            md_filepath = os.path.join(target_dir, md_filename)
            self._generate_markdown_evaluation_report(
                md_filepath, round_name, api_name, evaluation_results, test_results
            )

            if self.debug:
                print(f"Generated evaluation report: {md_filepath}")

            return md_filepath

        except Exception as e:
            raise ReportGeneratorError(f"Failed to generate evaluation report: {e}")

    def generate_comparison_report(
        self,
        api_name: str,
        all_evaluations: Dict[str, Dict[str, Any]],
        comparison_metrics: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a comparison report across all rounds for an API.

        Args:
            api_name: Name of the API
            all_evaluations: Dictionary of evaluations keyed by round name
            comparison_metrics: Optional comparison metrics from Evaluator

        Returns:
            str: Path to the generated report file

        Raises:
            ReportGeneratorError: If report generation fails
        """
        try:
            # Extract scores for analysis
            scores = {
                round_name: eval_result.get('score', 0)
                for round_name, eval_result in all_evaluations.items()
            }

            # Calculate statistics
            stats = self._calculate_statistics(scores)

            # Generate insights
            insights = self._generate_insights(scores, comparison_metrics)

            report = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'api': api_name,
                    'report_type': 'comparison',
                    'rounds_evaluated': len(all_evaluations)
                },
                'scores': scores,
                'statistics': stats,
                'comparison_metrics': comparison_metrics or {},
                'insights': insights,
                'evaluations': all_evaluations
            }

            # Generate filename
            filename = f"comparison_{api_name}.json"
            filepath = os.path.join(self.results_dir, filename)

            # Write report
            write_json(filepath, report)

            if self.debug:
                print(f"Generated comparison report: {filepath}")

            return filepath

        except Exception as e:
            raise ReportGeneratorError(f"Failed to generate comparison report: {e}")

    def generate_summary_report(
        self,
        all_results: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Generate a summary report across all APIs and rounds.

        Args:
            all_results: Dictionary of all results keyed by API name

        Returns:
            str: Path to the generated report file

        Raises:
            ReportGeneratorError: If report generation fails
        """
        try:
            # Aggregate data
            total_apis = len(all_results)
            all_scores = []
            api_summaries = {}

            for api_name, api_results in all_results.items():
                api_scores = [
                    eval_result.get('score', 0)
                    for eval_result in api_results.values()
                ]
                all_scores.extend(api_scores)

                api_summaries[api_name] = {
                    'rounds': len(api_results),
                    'average_score': sum(api_scores) / len(api_scores) if api_scores else 0,
                    'best_score': max(api_scores) if api_scores else 0,
                    'worst_score': min(api_scores) if api_scores else 0
                }

            # Calculate overall statistics
            overall_stats = self._calculate_statistics(
                {f"api_{i}": score for i, score in enumerate(all_scores)}
            )

            # Generate recommendations
            recommendations = self._generate_recommendations(api_summaries, overall_stats)

            report = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'report_type': 'summary',
                    'total_apis': total_apis
                },
                'overall_statistics': overall_stats,
                'api_summaries': api_summaries,
                'recommendations': recommendations
            }

            # Generate filename
            filename = f"summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self.results_dir, filename)

            # Write report
            write_json(filepath, report)

            if self.debug:
                print(f"Generated summary report: {filepath}")

            return filepath

        except Exception as e:
            raise ReportGeneratorError(f"Failed to generate summary report: {e}")

    def _generate_markdown_evaluation_report(
        self,
        filepath: str,
        round_name: str,
        api_name: str,
        evaluation_results: Dict[str, Any],
        test_results: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Generate a markdown evaluation report with detailed analysis from OpenAI.

        Args:
            filepath: Path to write the markdown report
            round_name: Name of the round
            api_name: Name of the API
            evaluation_results: Evaluation results from Evaluator
            test_results: Optional test results for detailed analysis
        """
        lines = []

        # Header
        lines.append(f"# Evaluation Report - {api_name} ({round_name})\n")
        lines.append(f"**Generated**: {datetime.now().isoformat()}\n\n")

        # Score Summary
        score = evaluation_results.get('score', 0)
        pass_rate = evaluation_results.get('pass_rate', 0)
        reasoning = evaluation_results.get('reasoning', '')

        lines.append("## Score Summary\n\n")
        lines.append(f"- **Overall Score**: {score}/100\n")
        lines.append(f"- **Pass Rate**: {pass_rate:.1f}%\n")
        lines.append(f"- **Status**: {self._get_score_status(score)}\n\n")

        # Get OpenAI Analysis
        lines.append("## Detailed Analysis\n\n")
        try:
            openai_client = OpenAIClient()
            analysis = openai_client.analyze_test_results(
                api_name=api_name,
                round_name=round_name,
                test_results=test_results or {},
                evaluation_score=score
            )
            lines.append(f"{analysis}\n\n")
        except OpenAIClientError as e:
            if self.debug:
                print(f"[DEBUG] OpenAI analysis failed: {e}")
            # Fallback to basic reasoning if OpenAI fails
            lines.append(f"{reasoning}\n\n")

        # Test Results Details
        if test_results:
            lines.append("## Test Results\n\n")

            passed = test_results.get('passed', 0)
            failed = test_results.get('failed', 0)
            errors = test_results.get('errors', 0)
            total = test_results.get('total', 0)

            lines.append("### Summary\n\n")
            lines.append(f"| Metric | Count |\n")
            lines.append(f"|--------|-------|\n")
            lines.append(f"| Passed | {passed} |\n")
            lines.append(f"| Failed | {failed} |\n")
            lines.append(f"| Errors | {errors} |\n")
            lines.append(f"| Total  | {total} |\n\n")

            # Detailed test results
            test_details = test_results.get('details', [])
            if test_details:
                lines.append("### Individual Test Results\n\n")

                passed_tests = [t for t in test_details if t.get('status') == 'PASSED']
                failed_tests = [t for t in test_details if t.get('status') == 'FAILED']
                error_tests = [t for t in test_details if t.get('status') == 'ERROR']

                if passed_tests:
                    lines.append("#### ✓ Passed Tests\n\n")
                    for test in passed_tests:
                        test_name = test.get('name', 'Unknown').split('::')[-1]
                        lines.append(f"- {test_name}\n")
                    lines.append("\n")

                if failed_tests:
                    lines.append("#### ✗ Failed Tests\n\n")
                    for test in failed_tests:
                        test_name = test.get('name', 'Unknown').split('::')[-1]
                        reason = test.get('reason', 'No reason provided')
                        lines.append(f"- **{test_name}**\n")
                        lines.append(f"  - Reason: {reason}\n")
                    lines.append("\n")

                if error_tests:
                    lines.append("#### ⚠ Error Tests\n\n")
                    for test in error_tests:
                        test_name = test.get('name', 'Unknown').split('::')[-1]
                        reason = test.get('reason', 'No reason provided')
                        lines.append(f"- **{test_name}**\n")
                        lines.append(f"  - Error: {reason}\n")
                    lines.append("\n")

        # Evaluation Details
        details = evaluation_results.get('details', {})
        if details:
            lines.append("## Evaluation Details\n\n")
            lines.append(f"- **Passed Tests**: {details.get('passed', 0)}\n")
            lines.append(f"- **Failed Tests**: {details.get('failed', 0)}\n")
            lines.append(f"- **Errors**: {details.get('errors', 0)}\n")
            lines.append(f"- **Total Tests**: {details.get('total', 0)}\n\n")

        # Score Interpretation
        lines.append("## Score Interpretation\n\n")
        lines.append(self._get_score_interpretation_markdown(score))
        lines.append("\n")

        # Write to file with UTF-8 encoding
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    def _get_score_status(self, score: int) -> str:
        """Get status label for a score."""
        if score >= 80:
            return "[PASS] Excellent"
        elif score >= 60:
            return "[PASS] Good"
        elif score >= 40:
            return "[WARN] Moderate"
        elif score >= 20:
            return "[FAIL] Poor"
        else:
            return "[FAIL] Failed"

    def _get_score_interpretation_markdown(self, score: int) -> str:
        """Get markdown interpretation of a score."""
        if score >= 80:
            return "**Excellent (80-100)**: The generated code demonstrates strong functionality with high test coverage. Production-ready with minimal issues."
        elif score >= 60:
            return "**Good (60-79)**: The generated code works well with most tests passing. Ready for use with minor fixes."
        elif score >= 40:
            return "**Moderate (40-59)**: The generated code has partial functionality with some test failures. Needs significant work before production use."
        elif score >= 20:
            return "**Poor (20-39)**: The generated code has limited functionality with many test failures. Major issues need to be addressed."
        else:
            return "**Failed (0-19)**: The generated code does not function properly. Requires complete rework."

    def _calculate_statistics(self, scores: Dict[str, float]) -> Dict[str, Any]:
        """
        Calculate statistics from scores.

        Args:
            scores: Dictionary of scores

        Returns:
            dict: Statistics including mean, median, min, max, std dev
        """
        if not scores:
            return {
                'count': 0,
                'mean': 0,
                'median': 0,
                'min': 0,
                'max': 0,
                'std_dev': 0
            }

        values = list(scores.values())
        values.sort()

        count = len(values)
        mean = sum(values) / count
        median = values[count // 2] if count % 2 == 1 else (values[count // 2 - 1] + values[count // 2]) / 2
        min_val = min(values)
        max_val = max(values)

        # Calculate standard deviation
        variance = sum((x - mean) ** 2 for x in values) / count
        std_dev = variance ** 0.5

        return {
            'count': count,
            'mean': round(mean, 2),
            'median': round(median, 2),
            'min': min_val,
            'max': max_val,
            'std_dev': round(std_dev, 2)
        }

    def _generate_insights(
        self,
        scores: Dict[str, float],
        comparison_metrics: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate insights from scores and comparison metrics.

        Args:
            scores: Dictionary of scores by round
            comparison_metrics: Optional comparison metrics

        Returns:
            list: List of insight strings
        """
        insights = []

        if not scores:
            return insights

        # Analyze trend
        if comparison_metrics:
            trend = comparison_metrics.get('trend', 'unknown')
            if trend == 'improving':
                insights.append("✓ Scores are improving across rounds - more information helps Claude")
            elif trend == 'declining':
                insights.append("✗ Scores are declining across rounds - additional information may be confusing")
            elif trend == 'stable':
                insights.append("→ Scores are stable across rounds - information type doesn't significantly impact results")

        # Analyze best round
        if comparison_metrics:
            best_round = comparison_metrics.get('best_round')
            if best_round:
                insights.append(f"Best performance: {best_round}")

        # Analyze average performance
        avg_score = sum(scores.values()) / len(scores)
        if avg_score >= 80:
            insights.append("Strong overall performance - Claude generates high-quality code")
        elif avg_score >= 60:
            insights.append("Moderate performance - Claude generates functional code with some issues")
        elif avg_score >= 40:
            insights.append("Weak performance - Claude struggles with this API")
        else:
            insights.append("Poor performance - Claude unable to generate working code")

        return insights

    def _generate_recommendations(
        self,
        api_summaries: Dict[str, Dict[str, Any]],
        overall_stats: Dict[str, Any]
    ) -> List[str]:
        """
        Generate recommendations based on results.

        Args:
            api_summaries: Summary statistics for each API
            overall_stats: Overall statistics

        Returns:
            list: List of recommendation strings
        """
        recommendations = []

        # Check overall performance
        overall_mean = overall_stats.get('mean', 0)
        if overall_mean < 50:
            recommendations.append("Consider providing more detailed API documentation to Claude")
            recommendations.append("Test with simpler APIs first to establish baseline performance")
        elif overall_mean < 70:
            recommendations.append("Provide example code snippets to improve Claude's understanding")
            recommendations.append("Include error handling examples in documentation")
        else:
            recommendations.append("Current information delivery is effective")
            recommendations.append("Consider testing with more complex APIs")

        # Check for high variance
        std_dev = overall_stats.get('std_dev', 0)
        if std_dev > 20:
            recommendations.append("High variance in results - information type significantly impacts performance")
            recommendations.append("Focus on optimizing the most effective information delivery method")

        # Check individual API performance
        for api_name, summary in api_summaries.items():
            if summary['average_score'] < 40:
                recommendations.append(f"API '{api_name}' has low performance - may need special handling")

        return recommendations

    def generate_html_report(
        self,
        json_report_path: str,
        output_filename: Optional[str] = None
    ) -> str:
        """
        Generate an HTML version of a JSON report.

        Args:
            json_report_path: Path to the JSON report file
            output_filename: Optional custom output filename

        Returns:
            str: Path to the generated HTML report

        Raises:
            ReportGeneratorError: If HTML generation fails
        """
        try:
            # Read JSON report
            with open(json_report_path, 'r') as f:
                report = json.load(f)

            # Generate HTML
            html_content = self._generate_html_content(report)

            # Determine output path
            if output_filename:
                html_path = os.path.join(self.results_dir, output_filename)
            else:
                base_name = os.path.splitext(os.path.basename(json_report_path))[0]
                html_path = os.path.join(self.results_dir, f"{base_name}.html")

            # Write HTML
            with open(html_path, 'w') as f:
                f.write(html_content)

            if self.debug:
                print(f"Generated HTML report: {html_path}")

            return html_path

        except Exception as e:
            raise ReportGeneratorError(f"Failed to generate HTML report: {e}")

    def _generate_html_content(self, report: Dict[str, Any]) -> str:
        """
        Generate HTML content from a report dictionary.

        Args:
            report: Report dictionary

        Returns:
            str: HTML content
        """
        report_type = report.get('metadata', {}).get('report_type', 'unknown')
        generated_at = report.get('metadata', {}).get('generated_at', 'Unknown')

        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI Readiness Evaluation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 20px; }}
        .metadata {{ background-color: #f9f9f9; padding: 10px; border-radius: 4px; margin-bottom: 20px; }}
        .score {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .stat-box {{ background-color: #f9f9f9; padding: 15px; border-radius: 4px; border-left: 4px solid #007bff; }}
        .stat-label {{ font-weight: bold; color: #555; }}
        .stat-value {{ font-size: 18px; color: #007bff; }}
        .insight {{ background-color: #e7f3ff; padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 4px solid #007bff; }}
        .recommendation {{ background-color: #fff3cd; padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 4px solid #ffc107; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #007bff; color: white; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Readiness Evaluation Report</h1>
        <div class="metadata">
            <p><strong>Generated:</strong> {}</p>
            <p><strong>Report Type:</strong> {}</p>
        </div>
""".format(generated_at, report_type)

        # Add content based on report type
        if report_type == 'evaluation':
            html += self._generate_evaluation_html(report)
        elif report_type == 'comparison':
            html += self._generate_comparison_html(report)
        elif report_type == 'summary':
            html += self._generate_summary_html(report)

        html += """
        <div class="footer">
            <p>Generated by AI Readiness Evaluator</p>
        </div>
    </div>
</body>
</html>
"""

        return html

    def _generate_evaluation_html(self, report: Dict[str, Any]) -> str:
        """Generate HTML for evaluation report."""
        evaluation = report.get('evaluation', {})
        score = evaluation.get('score', 0)
        pass_rate = evaluation.get('pass_rate', 0)
        reasoning = evaluation.get('reasoning', '')

        return f"""
        <h2>Evaluation Results</h2>
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-label">Score</div>
                <div class="stat-value">{score}/100</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Pass Rate</div>
                <div class="stat-value">{pass_rate:.1f}%</div>
            </div>
        </div>
        <h3>Reasoning</h3>
        <p>{reasoning}</p>
"""

    def _generate_comparison_html(self, report: Dict[str, Any]) -> str:
        """Generate HTML for comparison report."""
        scores = report.get('scores', {})
        insights = report.get('insights', [])

        html = "<h2>Round Comparison</h2>"
        html += "<table><tr><th>Round</th><th>Score</th></tr>"

        for round_name, score in scores.items():
            html += f"<tr><td>{round_name}</td><td>{score}</td></tr>"

        html += "</table>"

        if insights:
            html += "<h3>Insights</h3>"
            for insight in insights:
                html += f'<div class="insight">{insight}</div>'

        return html

    def _generate_summary_html(self, report: Dict[str, Any]) -> str:
        """Generate HTML for summary report."""
        stats = report.get('overall_statistics', {})
        recommendations = report.get('recommendations', [])

        html = "<h2>Overall Statistics</h2>"
        html += "<div class='stats-grid'>"

        for key, value in stats.items():
            html += f"""
            <div class="stat-box">
                <div class="stat-label">{key.replace('_', ' ').title()}</div>
                <div class="stat-value">{value}</div>
            </div>
"""

        html += "</div>"

        if recommendations:
            html += "<h3>Recommendations</h3>"
            for rec in recommendations:
                html += f'<div class="recommendation">{rec}</div>'

        return html

