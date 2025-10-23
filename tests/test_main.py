"""Tests for the main module."""

import os
import json
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from ai_evaluator.main import EvaluatorOrchestrator
from ai_evaluator.config import Config


class TestEvaluatorOrchestrator:
    """Test cases for the EvaluatorOrchestrator class."""

    def test_orchestrator_initialization(self):
        """Test that orchestrator initializes correctly."""
        orchestrator = EvaluatorOrchestrator()
        assert orchestrator.config == Config
        assert orchestrator.apis == {}
        assert orchestrator.prompts == {}
        assert orchestrator.results == {}

    def test_validate_configuration_success(self, capsys):
        """Test successful configuration validation."""
        orchestrator = EvaluatorOrchestrator()
        orchestrator._validate_configuration()
        captured = capsys.readouterr()
        assert "Validating configuration" in captured.out
        assert "Configuration validated successfully" in captured.out

    def test_load_configurations_success(self, capsys):
        """Test successful configuration loading."""
        orchestrator = EvaluatorOrchestrator()
        orchestrator._load_configurations()
        captured = capsys.readouterr()
        
        assert "Loading configurations" in captured.out
        assert "Loaded" in captured.out
        assert len(orchestrator.apis) > 0
        assert len(orchestrator.prompts) > 0

    def test_load_configurations_apis(self):
        """Test that APIs are loaded correctly."""
        orchestrator = EvaluatorOrchestrator()
        orchestrator._load_configurations()
        
        # Check that expected APIs are loaded
        assert "OPEN_METEO_WEATHER" in orchestrator.apis
        assert "SWAPI_PEOPLE" in orchestrator.apis
        
        # Check API structure
        api = orchestrator.apis["OPEN_METEO_WEATHER"]
        assert "curl_command" in api
        assert "description" in api
        assert "documentation_url" in api

    def test_load_configurations_prompts(self):
        """Test that prompts are loaded correctly."""
        orchestrator = EvaluatorOrchestrator()
        orchestrator._load_configurations()
        
        # Check that expected prompts are loaded
        assert "ROUND_1_CURL_ONLY" in orchestrator.prompts
        assert "ROUND_2_WITH_DOCS" in orchestrator.prompts
        assert "ROUND_3_WITH_POSTMAN" in orchestrator.prompts
        assert "ROUND_4_WITH_EXAMPLES" in orchestrator.prompts
        
        # Check prompt content
        for prompt_name, prompt_text in orchestrator.prompts.items():
            assert isinstance(prompt_text, str)
            assert len(prompt_text) > 0

    def test_print_startup_info(self, capsys):
        """Test startup information printing."""
        orchestrator = EvaluatorOrchestrator()
        orchestrator._load_configurations()
        orchestrator._print_startup_info()
        captured = capsys.readouterr()
        
        assert "STARTUP INFORMATION" in captured.out
        assert "APIs to evaluate" in captured.out
        assert "Rounds to execute" in captured.out

    def test_run_evaluations(self, capsys):
        """Test evaluation execution."""
        orchestrator = EvaluatorOrchestrator()
        orchestrator._load_configurations()
        orchestrator._run_evaluations()
        captured = capsys.readouterr()
        
        assert "Starting evaluations" in captured.out
        assert "Evaluating API" in captured.out
        
        # Check results structure
        assert len(orchestrator.results) > 0
        for api_name, api_results in orchestrator.results.items():
            assert isinstance(api_results, dict)
            for round_name, result in api_results.items():
                assert "status" in result
                assert "message" in result

    def test_generate_reports(self):
        """Test report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Override results directory
            original_results_dir = Config.RESULTS_DIR
            Config.RESULTS_DIR = tmpdir
            
            try:
                orchestrator = EvaluatorOrchestrator()
                orchestrator._load_configurations()
                orchestrator._run_evaluations()
                orchestrator._generate_reports()
                
                # Check that comparison report was created
                report_path = os.path.join(tmpdir, "comparison_report.json")
                assert os.path.exists(report_path)
                
                # Check report content
                with open(report_path, 'r') as f:
                    report = json.load(f)
                
                assert "summary" in report
                assert "results" in report
                assert report["summary"]["total_apis"] > 0
                assert report["summary"]["total_rounds"] > 0
                
            finally:
                Config.RESULTS_DIR = original_results_dir

    def test_generate_reports_creates_directories(self):
        """Test that report generation creates directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_results_dir = Config.RESULTS_DIR
            Config.RESULTS_DIR = tmpdir
            
            try:
                orchestrator = EvaluatorOrchestrator()
                orchestrator._load_configurations()
                orchestrator._run_evaluations()
                orchestrator._generate_reports()
                
                # Check that round directories were created
                for round_name in orchestrator.prompts.keys():
                    round_dir = os.path.join(tmpdir, round_name.lower())
                    assert os.path.exists(round_dir)
                    
                    # Check that API subdirectories were created
                    for api_name in orchestrator.apis.keys():
                        api_dir = os.path.join(round_dir, api_name.lower())
                        assert os.path.exists(api_dir)
                        
            finally:
                Config.RESULTS_DIR = original_results_dir

    def test_print_completion_info(self, capsys):
        """Test completion information printing."""
        orchestrator = EvaluatorOrchestrator()
        orchestrator._load_configurations()
        orchestrator._run_evaluations()
        orchestrator._print_completion_info()
        captured = capsys.readouterr()
        
        assert "EVALUATION COMPLETE" in captured.out
        assert "Results saved to" in captured.out
        assert "Total APIs evaluated" in captured.out
        assert "Total rounds executed" in captured.out

    def test_run_success(self):
        """Test successful orchestrator run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_results_dir = Config.RESULTS_DIR
            Config.RESULTS_DIR = tmpdir
            
            try:
                orchestrator = EvaluatorOrchestrator()
                exit_code = orchestrator.run()
                
                assert exit_code == 0
                assert len(orchestrator.apis) > 0
                assert len(orchestrator.prompts) > 0
                assert len(orchestrator.results) > 0
                
            finally:
                Config.RESULTS_DIR = original_results_dir

    def test_run_with_debug_mode(self, capsys):
        """Test orchestrator run with debug mode enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_results_dir = Config.RESULTS_DIR
            original_debug_mode = Config.DEBUG_MODE
            Config.RESULTS_DIR = tmpdir
            Config.DEBUG_MODE = True
            
            try:
                orchestrator = EvaluatorOrchestrator()
                exit_code = orchestrator.run()
                
                assert exit_code == 0
                
            finally:
                Config.RESULTS_DIR = original_results_dir
                Config.DEBUG_MODE = original_debug_mode

    def test_run_handles_errors(self):
        """Test that orchestrator handles errors gracefully."""
        orchestrator = EvaluatorOrchestrator()
        
        # Mock _validate_configuration to raise an error
        with patch.object(orchestrator, '_validate_configuration', side_effect=Exception("Test error")):
            exit_code = orchestrator.run()
            assert exit_code == 1

    def test_results_structure(self):
        """Test that results have the correct structure."""
        orchestrator = EvaluatorOrchestrator()
        orchestrator._load_configurations()
        orchestrator._run_evaluations()
        
        # Verify results structure
        for api_name, api_results in orchestrator.results.items():
            assert api_name in orchestrator.apis
            
            for round_name, result in api_results.items():
                assert round_name in orchestrator.prompts
                assert isinstance(result, dict)
                assert "status" in result
                assert "message" in result

