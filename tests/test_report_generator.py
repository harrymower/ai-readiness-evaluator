"""Tests for the report generator module."""

import pytest
import tempfile
import os
import json
from ai_evaluator.report_generator import ReportGenerator, ReportGeneratorError


class TestReportGeneratorInitialization:
    """Test cases for ReportGenerator initialization."""

    def test_initialization(self):
        """Test that report generator initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)
            assert generator.results_dir == tmpdir
            assert os.path.exists(tmpdir)

    def test_creates_results_directory(self):
        """Test that results directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = os.path.join(tmpdir, "results")
            assert not os.path.exists(results_dir)

            generator = ReportGenerator(results_dir)
            assert os.path.exists(results_dir)


class TestGenerateEvaluationReport:
    """Test cases for evaluation report generation."""

    def test_generate_evaluation_report(self):
        """Test generating an evaluation report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            evaluation_results = {
                'score': 85,
                'pass_rate': 85.0,
                'success': True,
                'reasoning': 'Good performance',
                'details': {'passed': 17, 'failed': 3, 'total': 20}
            }

            filepath = generator.generate_evaluation_report(
                round_name='ROUND_1',
                api_name='TEST_API',
                evaluation_results=evaluation_results
            )

            assert os.path.exists(filepath)
            assert 'evaluation_TEST_API_ROUND_1.json' in filepath

            # Verify content
            with open(filepath, 'r') as f:
                report = json.load(f)

            assert report['metadata']['round'] == 'ROUND_1'
            assert report['metadata']['api'] == 'TEST_API'
            assert report['evaluation']['score'] == 85

    def test_generate_evaluation_report_with_code_snippets(self):
        """Test generating evaluation report with code snippets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            evaluation_results = {'score': 90, 'pass_rate': 90.0}
            code_snippet = "print('hello')"
            test_snippet = "assert True"

            filepath = generator.generate_evaluation_report(
                round_name='ROUND_2',
                api_name='API_TEST',
                evaluation_results=evaluation_results,
                code_snippet=code_snippet,
                test_snippet=test_snippet
            )

            with open(filepath, 'r') as f:
                report = json.load(f)

            assert report['code_snippet'] == code_snippet
            assert report['test_snippet'] == test_snippet


class TestGenerateComparisonReport:
    """Test cases for comparison report generation."""

    def test_generate_comparison_report(self):
        """Test generating a comparison report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            all_evaluations = {
                'ROUND_1': {'score': 60, 'pass_rate': 60.0},
                'ROUND_2': {'score': 75, 'pass_rate': 75.0},
                'ROUND_3': {'score': 85, 'pass_rate': 85.0}
            }

            comparison_metrics = {
                'best_round': 'ROUND_3',
                'worst_round': 'ROUND_1',
                'improvement': 25,
                'trend': 'improving'
            }

            filepath = generator.generate_comparison_report(
                api_name='TEST_API',
                all_evaluations=all_evaluations,
                comparison_metrics=comparison_metrics
            )

            assert os.path.exists(filepath)
            assert 'comparison_TEST_API.json' in filepath

            with open(filepath, 'r') as f:
                report = json.load(f)

            assert report['metadata']['api'] == 'TEST_API'
            assert report['scores']['ROUND_1'] == 60
            assert report['comparison_metrics']['trend'] == 'improving'

    def test_comparison_report_statistics(self):
        """Test that comparison report includes statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            all_evaluations = {
                'ROUND_1': {'score': 50},
                'ROUND_2': {'score': 70},
                'ROUND_3': {'score': 90}
            }

            filepath = generator.generate_comparison_report(
                api_name='API',
                all_evaluations=all_evaluations
            )

            with open(filepath, 'r') as f:
                report = json.load(f)

            stats = report['statistics']
            assert stats['count'] == 3
            assert stats['mean'] == 70.0
            assert stats['min'] == 50
            assert stats['max'] == 90


class TestGenerateSummaryReport:
    """Test cases for summary report generation."""

    def test_generate_summary_report(self):
        """Test generating a summary report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            all_results = {
                'API_1': {
                    'ROUND_1': {'score': 70},
                    'ROUND_2': {'score': 80}
                },
                'API_2': {
                    'ROUND_1': {'score': 60},
                    'ROUND_2': {'score': 75}
                }
            }

            filepath = generator.generate_summary_report(all_results)

            assert os.path.exists(filepath)
            assert 'summary_report_' in filepath

            with open(filepath, 'r') as f:
                report = json.load(f)

            assert report['metadata']['total_apis'] == 2
            assert 'API_1' in report['api_summaries']
            assert 'API_2' in report['api_summaries']

    def test_summary_report_api_summaries(self):
        """Test that summary report includes API summaries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            all_results = {
                'API_1': {
                    'ROUND_1': {'score': 60},
                    'ROUND_2': {'score': 80}
                }
            }

            filepath = generator.generate_summary_report(all_results)

            with open(filepath, 'r') as f:
                report = json.load(f)

            api_summary = report['api_summaries']['API_1']
            assert api_summary['rounds'] == 2
            assert api_summary['average_score'] == 70.0
            assert api_summary['best_score'] == 80
            assert api_summary['worst_score'] == 60


class TestCalculateStatistics:
    """Test cases for statistics calculation."""

    def test_calculate_statistics_basic(self):
        """Test basic statistics calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            scores = {'a': 50, 'b': 60, 'c': 70}
            stats = generator._calculate_statistics(scores)

            assert stats['count'] == 3
            assert stats['mean'] == 60.0
            assert stats['min'] == 50
            assert stats['max'] == 70

    def test_calculate_statistics_empty(self):
        """Test statistics with empty scores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            stats = generator._calculate_statistics({})

            assert stats['count'] == 0
            assert stats['mean'] == 0
            assert stats['median'] == 0

    def test_calculate_statistics_median(self):
        """Test median calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            # Odd number of values
            scores = {'a': 10, 'b': 20, 'c': 30}
            stats = generator._calculate_statistics(scores)
            assert stats['median'] == 20

            # Even number of values
            scores = {'a': 10, 'b': 20, 'c': 30, 'd': 40}
            stats = generator._calculate_statistics(scores)
            assert stats['median'] == 25.0


class TestGenerateInsights:
    """Test cases for insight generation."""

    def test_generate_insights_improving(self):
        """Test insights for improving trend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            scores = {'ROUND_1': 50, 'ROUND_2': 70, 'ROUND_3': 90}
            comparison_metrics = {'trend': 'improving', 'best_round': 'ROUND_3'}

            insights = generator._generate_insights(scores, comparison_metrics)

            assert any('improving' in insight.lower() for insight in insights)

    def test_generate_insights_declining(self):
        """Test insights for declining trend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            scores = {'ROUND_1': 90, 'ROUND_2': 70, 'ROUND_3': 50}
            comparison_metrics = {'trend': 'declining'}

            insights = generator._generate_insights(scores, comparison_metrics)

            assert any('declining' in insight.lower() for insight in insights)


class TestGenerateRecommendations:
    """Test cases for recommendation generation."""

    def test_generate_recommendations_low_performance(self):
        """Test recommendations for low performance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            api_summaries = {'API_1': {'average_score': 30}}
            overall_stats = {'mean': 30}

            recommendations = generator._generate_recommendations(api_summaries, overall_stats)

            assert len(recommendations) > 0
            assert any('documentation' in rec.lower() for rec in recommendations)

    def test_generate_recommendations_high_variance(self):
        """Test recommendations for high variance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            api_summaries = {'API_1': {'average_score': 70}}
            overall_stats = {'mean': 70, 'std_dev': 25}

            recommendations = generator._generate_recommendations(api_summaries, overall_stats)

            assert any('variance' in rec.lower() for rec in recommendations)


class TestGenerateHtmlReport:
    """Test cases for HTML report generation."""

    def test_generate_html_report_from_json(self):
        """Test generating HTML report from JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            # Create a JSON report first
            evaluation_results = {'score': 85, 'pass_rate': 85.0}
            json_path = generator.generate_evaluation_report(
                round_name='ROUND_1',
                api_name='TEST_API',
                evaluation_results=evaluation_results
            )

            # Generate HTML from JSON
            html_path = generator.generate_html_report(json_path)

            assert os.path.exists(html_path)
            assert html_path.endswith('.html')

            # Verify HTML content
            with open(html_path, 'r') as f:
                html_content = f.read()

            assert '<!DOCTYPE html>' in html_content
            assert 'AI Readiness Evaluation Report' in html_content

    def test_generate_html_report_custom_filename(self):
        """Test generating HTML with custom filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            evaluation_results = {'score': 90}
            json_path = generator.generate_evaluation_report(
                round_name='ROUND_1',
                api_name='API',
                evaluation_results=evaluation_results
            )

            html_path = generator.generate_html_report(
                json_path,
                output_filename='custom_report.html'
            )

            assert 'custom_report.html' in html_path
            assert os.path.exists(html_path)


class TestReportGeneratorErrors:
    """Test cases for error handling."""

    def test_generate_html_report_missing_json(self):
        """Test error when JSON file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(tmpdir)

            with pytest.raises(ReportGeneratorError):
                generator.generate_html_report('nonexistent.json')

