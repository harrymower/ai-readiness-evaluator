"""
Tests for LLM analyzer.

Unit tests for prompt building, LLM calls, retry logic, and fallback mechanism.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from api_analysis.analyzers.llm import (
    build_analysis_prompt,
    analyze_with_llm,
    LLM_RESPONSE_SCHEMA
)
from api_analysis.models import LLMAnalysisResult


class TestBuildAnalysisPrompt:
    """Tests for build_analysis_prompt function."""
    
    def test_basic_prompt(self):
        """Test basic prompt building."""
        prompt = build_analysis_prompt(
            api_name="Test API",
            doc_content="API Documentation content here",
            programmatic_results=None
        )
        
        assert "Test API" in prompt
        assert "API Documentation content here" in prompt
        assert "total_endpoints" in prompt
    
    def test_with_programmatic_results(self):
        """Test prompt with programmatic results."""
        prog_results = {
            'schema_depth': 'medium',
            'pagination_supported': True,
            'rate_limiting': 'simple'
        }
        
        prompt = build_analysis_prompt(
            api_name="Test API",
            doc_content="Docs",
            programmatic_results=prog_results
        )
        
        assert "medium" in prompt
        assert "simple" in prompt


class TestAnalyzeWithLLM:
    """Tests for analyze_with_llm function."""
    
    @patch('api_analysis.analyzers.llm.GeminiProvider')
    @patch('api_analysis.analyzers.llm.get_config')
    def test_successful_analysis(self, mock_config, mock_provider_class):
        """Test successful LLM analysis."""
        # Mock config
        mock_cfg = Mock()
        mock_cfg.get_api_key.return_value = 'test-key'
        mock_cfg.confidence_threshold = 0.7
        mock_config.return_value = mock_cfg
        
        # Mock provider
        mock_provider = Mock()
        mock_provider.analyze.return_value = {
            'total_endpoints': 10,
            'auth_required': 'yes',
            'parameter_complexity': 'medium',
            'error_surface': 'high',
            'error_codes_count': 5,
            'doc_coverage': 'high',
            'reasoning': {
                'total_endpoints': '10 endpoints found',
                'auth_required': 'All require auth',
                'parameter_complexity': 'Moderate params',
                'error_surface': 'Many error types',
                'error_codes_count': '5 codes',
                'doc_coverage': 'Good docs'
            },
            'confidence': {
                'total_endpoints': 0.9,
                'auth_required': 0.95,
                'parameter_complexity': 0.8,
                'error_surface': 0.85,
                'error_codes_count': 0.9,
                'doc_coverage': 0.9
            }
        }
        mock_provider_class.return_value = mock_provider
        
        result = analyze_with_llm(
            api_name="Test API",
            documentation="API docs here",
            llm_provider='gemini-2.0-flash'
        )
        
        assert isinstance(result, LLMAnalysisResult)
        assert result.total_endpoints == 10
        assert result.auth_required == 'yes'
        assert result.average_confidence > 0.8
    
    @patch('api_analysis.analyzers.llm.GeminiProvider')
    @patch('api_analysis.analyzers.llm.OpenAIProvider')
    @patch('api_analysis.analyzers.llm.get_config')
    def test_fallback_to_gpt(self, mock_config, mock_openai_class, mock_gemini_class):
        """Test fallback from Gemini to GPT on failure."""
        # Mock config
        mock_cfg = Mock()
        mock_cfg.get_api_key.return_value = 'test-key'
        mock_config.return_value = mock_cfg
        
        # Mock Gemini provider to fail
        mock_gemini = Mock()
        mock_gemini.analyze.side_effect = Exception("Rate limit")
        mock_gemini_class.return_value = mock_gemini
        
        # Mock OpenAI provider to succeed
        mock_openai = Mock()
        mock_openai.analyze.return_value = {
            'total_endpoints': 5,
            'auth_required': 'no',
            'parameter_complexity': 'low',
            'error_surface': 'low',
            'error_codes_count': 2,
            'doc_coverage': 'medium',
            'reasoning': {'total_endpoints': 'Found 5'},
            'confidence': {'total_endpoints': 0.8}
        }
        mock_openai_class.return_value = mock_openai
        
        # Should not raise, should fall back
        result = analyze_with_llm(
            api_name="Test API",
            documentation="API docs",
            llm_provider='gemini-2.0-flash',
            max_retries=1  # Reduce retries for faster test
        )
        
        assert result.total_endpoints == 5
    
    @patch('api_analysis.analyzers.llm.get_config')
    def test_missing_api_key(self, mock_config):
        """Test handling of missing API key."""
        mock_cfg = Mock()
        mock_cfg.get_api_key.side_effect = ValueError("API key not found")
        mock_config.return_value = mock_cfg
        
        with pytest.raises(Exception):
            analyze_with_llm(
                api_name="Test API",
                documentation="Docs",
                llm_provider='gemini-2.0-flash'
            )


class TestIntegrationWithLLM:
    """Integration tests with real LLM calls (gated by environment variable)."""
    
    @pytest.mark.skipif(
        os.getenv('ENABLE_LLM_TESTS') != 'true',
        reason="Set ENABLE_LLM_TESTS=true to run (costs money!)"
    )
    def test_real_gemini_call(self):
        """Test real Gemini API call."""
        result = analyze_with_llm(
            api_name="Test API",
            documentation="""
            # Test API Documentation
            
            ## Endpoints
            - GET /users - List all users
            - POST /users - Create a user
            
            ## Authentication
            All endpoints require an API key in the header.
            
            ## Errors
            - 400: Bad Request
            - 401: Unauthorized
            - 404: Not Found
            """,
            llm_provider='gemini-2.0-flash'
        )
        
        assert isinstance(result, LLMAnalysisResult)
        assert result.total_endpoints > 0
        assert result.average_confidence > 0.5
