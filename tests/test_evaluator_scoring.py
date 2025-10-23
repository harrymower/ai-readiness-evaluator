"""Tests for the evaluator module."""

import pytest
import tempfile
import os
from ai_evaluator.evaluator import Evaluator, EvaluatorError


class TestEvaluatorInitialization:
    """Test cases for Evaluator initialization."""

    def test_evaluator_initialization(self):
        """Test that evaluator initializes correctly."""
        evaluator = Evaluator()
        assert evaluator.debug is not None


class TestEvaluate:
    """Test cases for the evaluate method."""

    def test_evaluate_success(self):
        """Test successful evaluation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('hello')")
            cli_tool = f.name
        
        try:
            test_results = {
                'passed': 5,
                'failed': 0,
                'errors': 0,
                'total': 5,
                'success': True
            }
            
            evaluator = Evaluator()
            result = evaluator.evaluate(cli_tool, test_results)
            
            assert 'score' in result
            assert 'pass_rate' in result
            assert 'reasoning' in result
            assert 'details' in result
            assert result['pass_rate'] == 100.0
            assert result['success'] is True
            
        finally:
            os.unlink(cli_tool)

    def test_evaluate_with_failures(self):
        """Test evaluation with test failures."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('hello')")
            cli_tool = f.name
        
        try:
            test_results = {
                'passed': 3,
                'failed': 2,
                'errors': 0,
                'total': 5,
                'success': False
            }
            
            evaluator = Evaluator()
            result = evaluator.evaluate(cli_tool, test_results)
            
            assert result['pass_rate'] == 60.0
            assert result['success'] is True  # 60% is >= 50%
            
        finally:
            os.unlink(cli_tool)

    def test_evaluate_with_errors(self):
        """Test evaluation with test errors."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('hello')")
            cli_tool = f.name
        
        try:
            test_results = {
                'passed': 2,
                'failed': 1,
                'errors': 2,
                'total': 5,
                'success': False
            }
            
            evaluator = Evaluator()
            result = evaluator.evaluate(cli_tool, test_results)
            
            assert result['pass_rate'] == 40.0
            assert result['success'] is False  # 40% is < 50%
            
        finally:
            os.unlink(cli_tool)

    def test_evaluate_cli_tool_not_found(self):
        """Test error when CLI tool doesn't exist."""
        test_results = {
            'passed': 5,
            'failed': 0,
            'errors': 0,
            'total': 5
        }
        
        evaluator = Evaluator()
        with pytest.raises(EvaluatorError) as exc_info:
            evaluator.evaluate("nonexistent_tool.py", test_results)
        
        assert "CLI tool not found" in str(exc_info.value)

    def test_evaluate_with_code_quality_metrics(self):
        """Test evaluation with code quality metrics."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('hello')")
            cli_tool = f.name
        
        try:
            test_results = {
                'passed': 5,
                'failed': 0,
                'errors': 0,
                'total': 5
            }
            
            quality_metrics = {
                'code_length': 100,
                'has_error_handling': True,
                'has_documentation': True,
                'follows_conventions': True
            }
            
            evaluator = Evaluator()
            result = evaluator.evaluate(cli_tool, test_results, quality_metrics)
            
            # Score should be higher with quality metrics
            assert result['score'] > 80
            
        finally:
            os.unlink(cli_tool)


class TestCalculateGradientScore:
    """Test cases for gradient scoring."""

    def test_score_100_percent_pass_rate(self):
        """Test score with 100% pass rate."""
        evaluator = Evaluator()
        score = evaluator._calculate_gradient_score(pass_rate=100.0)
        assert score == 90  # 100 * 0.9

    def test_score_50_percent_pass_rate(self):
        """Test score with 50% pass rate."""
        evaluator = Evaluator()
        score = evaluator._calculate_gradient_score(pass_rate=50.0)
        assert score == 45  # 50 * 0.9

    def test_score_0_percent_pass_rate(self):
        """Test score with 0% pass rate."""
        evaluator = Evaluator()
        score = evaluator._calculate_gradient_score(pass_rate=0.0)
        assert score == 0

    def test_score_with_quality_bonus(self):
        """Test score with quality bonus."""
        evaluator = Evaluator()
        quality_metrics = {
            'code_length': 100,
            'has_error_handling': True,
            'has_documentation': True,
            'follows_conventions': True
        }
        score = evaluator._calculate_gradient_score(pass_rate=90.0, code_quality_metrics=quality_metrics)
        assert score > 81  # 90 * 0.9 + bonus


class TestCalculateQualityBonus:
    """Test cases for quality bonus calculation."""

    def test_quality_bonus_no_metrics(self):
        """Test quality bonus with no metrics."""
        evaluator = Evaluator()
        bonus = evaluator._calculate_quality_bonus(None)
        assert bonus == 0

    def test_quality_bonus_all_metrics(self):
        """Test quality bonus with all metrics."""
        evaluator = Evaluator()
        metrics = {
            'code_length': 100,
            'has_error_handling': True,
            'has_documentation': True,
            'follows_conventions': True
        }
        bonus = evaluator._calculate_quality_bonus(metrics)
        assert bonus == 10  # Max bonus

    def test_quality_bonus_partial_metrics(self):
        """Test quality bonus with partial metrics."""
        evaluator = Evaluator()
        metrics = {
            'code_length': 100,
            'has_error_handling': True,
            'has_documentation': False,
            'follows_conventions': False
        }
        bonus = evaluator._calculate_quality_bonus(metrics)
        assert bonus == 5  # 2 + 3

    def test_quality_bonus_code_length_too_short(self):
        """Test quality bonus with code too short."""
        evaluator = Evaluator()
        metrics = {
            'code_length': 10,
            'has_error_handling': True,
            'has_documentation': True,
            'follows_conventions': True
        }
        bonus = evaluator._calculate_quality_bonus(metrics)
        assert bonus == 8  # No length bonus


class TestCalculateScore:
    """Test cases for calculate_score method."""

    def test_calculate_score_all_passed(self):
        """Test score calculation with all tests passed."""
        test_results = {
            'passed': 5,
            'failed': 0,
            'errors': 0,
            'total': 5
        }
        
        evaluator = Evaluator()
        score = evaluator.calculate_score(test_results)
        assert score == 90  # 100% * 0.9

    def test_calculate_score_partial_passed(self):
        """Test score calculation with partial tests passed."""
        test_results = {
            'passed': 3,
            'failed': 2,
            'errors': 0,
            'total': 5
        }
        
        evaluator = Evaluator()
        score = evaluator.calculate_score(test_results)
        assert score == 54  # 60% * 0.9

    def test_calculate_score_no_tests(self):
        """Test score calculation with no tests."""
        test_results = {
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'total': 0
        }
        
        evaluator = Evaluator()
        score = evaluator.calculate_score(test_results)
        assert score == 0


class TestGenerateReasoning:
    """Test cases for reasoning generation."""

    def test_reasoning_excellent_score(self):
        """Test reasoning for excellent score."""
        evaluator = Evaluator()
        reasoning = evaluator._generate_reasoning(
            score=85,
            pass_rate=95.0,
            passed=19,
            failed=1,
            errors=0,
            total=20
        )
        
        assert "Excellent" in reasoning
        assert "95.0%" in reasoning

    def test_reasoning_good_score(self):
        """Test reasoning for good score."""
        evaluator = Evaluator()
        reasoning = evaluator._generate_reasoning(
            score=70,
            pass_rate=80.0,
            passed=4,
            failed=1,
            errors=0,
            total=5
        )
        
        assert "Good" in reasoning
        assert "80.0%" in reasoning

    def test_reasoning_failed_score(self):
        """Test reasoning for failed score."""
        evaluator = Evaluator()
        reasoning = evaluator._generate_reasoning(
            score=10,
            pass_rate=10.0,
            passed=1,
            failed=9,
            errors=0,
            total=10
        )
        
        assert "Failed" in reasoning
        assert "10.0%" in reasoning

    def test_reasoning_no_tests(self):
        """Test reasoning when no tests executed."""
        evaluator = Evaluator()
        reasoning = evaluator._generate_reasoning(
            score=0,
            pass_rate=0.0,
            passed=0,
            failed=0,
            errors=0,
            total=0
        )
        
        assert "No tests" in reasoning


class TestCompareEvaluations:
    """Test cases for comparing evaluations."""

    def test_compare_evaluations_single(self):
        """Test comparing single evaluation."""
        evaluations = {
            'ROUND_1': {'score': 50, 'pass_rate': 50.0}
        }
        
        evaluator = Evaluator()
        comparison = evaluator.compare_evaluations(evaluations)
        
        assert comparison['best_round'] == 'ROUND_1'
        assert comparison['worst_round'] == 'ROUND_1'
        assert comparison['average_score'] == 50

    def test_compare_evaluations_multiple_improving(self):
        """Test comparing multiple improving evaluations."""
        evaluations = {
            'ROUND_1': {'score': 40, 'pass_rate': 40.0},
            'ROUND_2': {'score': 60, 'pass_rate': 60.0},
            'ROUND_3': {'score': 80, 'pass_rate': 80.0}
        }
        
        evaluator = Evaluator()
        comparison = evaluator.compare_evaluations(evaluations)
        
        assert comparison['best_round'] == 'ROUND_3'
        assert comparison['worst_round'] == 'ROUND_1'
        assert comparison['improvement'] == 40
        assert comparison['trend'] == 'improving'

    def test_compare_evaluations_multiple_declining(self):
        """Test comparing multiple declining evaluations."""
        evaluations = {
            'ROUND_1': {'score': 80, 'pass_rate': 80.0},
            'ROUND_2': {'score': 60, 'pass_rate': 60.0},
            'ROUND_3': {'score': 40, 'pass_rate': 40.0}
        }
        
        evaluator = Evaluator()
        comparison = evaluator.compare_evaluations(evaluations)
        
        assert comparison['improvement'] == -40
        assert comparison['trend'] == 'declining'

    def test_compare_evaluations_empty(self):
        """Test error when comparing empty evaluations."""
        evaluator = Evaluator()
        with pytest.raises(EvaluatorError):
            evaluator.compare_evaluations({})


class TestGetScoreInterpretation:
    """Test cases for score interpretation."""

    def test_interpretation_excellent(self):
        """Test interpretation for excellent score."""
        evaluator = Evaluator()
        interpretation = evaluator.get_score_interpretation(85)
        assert "Excellent" in interpretation

    def test_interpretation_good(self):
        """Test interpretation for good score."""
        evaluator = Evaluator()
        interpretation = evaluator.get_score_interpretation(70)
        assert "Good" in interpretation

    def test_interpretation_moderate(self):
        """Test interpretation for moderate score."""
        evaluator = Evaluator()
        interpretation = evaluator.get_score_interpretation(50)
        assert "Moderate" in interpretation

    def test_interpretation_poor(self):
        """Test interpretation for poor score."""
        evaluator = Evaluator()
        interpretation = evaluator.get_score_interpretation(25)
        assert "Poor" in interpretation

    def test_interpretation_failed(self):
        """Test interpretation for failed score."""
        evaluator = Evaluator()
        interpretation = evaluator.get_score_interpretation(10)
        assert "Failed" in interpretation

