"""
Tests for validation and merging logic.

Unit tests for result merging, cross-validation, confidence filtering, and YAML generation.
"""

import pytest
from api_analysis.validators.merger import (
    merge_results,
    cross_validate,
    apply_confidence_filtering,
    validate_enums,
    validate_and_merge
)
from api_analysis.outputs.yaml_generator import generate_yaml_entry, generate_yaml_file
from api_analysis.models import LLMAnalysisResult, APIMetadata, AnalysisResult


class TestMergeResults:
    """Tests for merge_results function."""
    
    def test_basic_merge(self):
        """Test basic merging of programmatic and LLM results."""
        programmatic = {
            'avg_response_size_kb': 12.5,
            'schema_depth': 'medium',
            'pagination_supported': True,
            'pagination_pattern': 'offset_limit',
            'rate_limiting': 'simple',
            'auth_detected': False
        }
        
        llm = LLMAnalysisResult(
            total_endpoints=20,
            auth_required='optional',
            parameter_complexity='medium',
            error_surface='high',
            error_codes_count=6,
            doc_coverage='high',
            reasoning={'total_endpoints': 'Counted 20'},
            confidence={'total_endpoints': 0.9}
        )
        
        merged = merge_results(programmatic, llm)
        
        # Objective fields from programmatic
        assert merged['avg_response_size_kb'] == 12.5
        assert merged['schema_depth'] == 'medium'
        assert merged['pagination_pattern'] == 'offset_limit'
        
        # Subjective fields from LLM
        assert merged['total_endpoints'] == 20
        assert merged['parameter_complexity'] == 'medium'
        assert merged['doc_coverage'] == 'high'
    
    def test_auth_detection_override(self):
        """Test that programmatic auth detection overrides LLM."""
        programmatic = {'auth_detected': True}
        llm = LLMAnalysisResult(
            total_endpoints=10,
            auth_required='no',
            parameter_complexity='low',
            error_surface='low',
            error_codes_count=2,
            doc_coverage='medium',
            reasoning={},
            confidence={}
        )
        
        merged = merge_results(programmatic, llm)
        
        assert merged['auth_required'] == 'yes'  # Programmatic detected auth


class TestCrossValidate:
    """Tests for cross_validate function."""
    
    def test_auth_conflict(self):
        """Test detection of auth requirement conflicts."""
        merged = {'auth_required': 'yes'}
        programmatic = {'auth_detected': False}
        llm = LLMAnalysisResult(
            total_endpoints=10,
            auth_required='yes',
            parameter_complexity='low',
            error_surface='low',
            error_codes_count=2,
            doc_coverage='medium',
            reasoning={},
            confidence={}
        )
        
        flags = cross_validate(merged, programmatic, llm)
        
        assert len(flags) > 0
        assert any('auth' in flag.lower() for flag in flags)


class TestConfidenceFiltering:
    """Tests for apply_confidence_filtering function."""
    
    def test_low_confidence_filtering(self):
        """Test that low confidence fields are set to unknown."""
        merged = {
            'total_endpoints': 10,
            'auth_required': 'yes',
            'parameter_complexity': 'medium',
            'doc_coverage': 'high'
        }
        
        confidence = {
            'total_endpoints': 0.9,
            'auth_required': 0.5,  # Below threshold
            'parameter_complexity': 0.8,
            'doc_coverage': 0.4  # Below threshold
        }
        
        filtered, flags = apply_confidence_filtering(merged, confidence, threshold=0.7)
        
        # Low confidence enum fields should be 'unknown'
        assert filtered['auth_required'] == 'unknown'
        assert filtered['doc_coverage'] == 'unknown'
        
        # High confidence fields unchanged
        assert filtered['parameter_complexity'] == 'medium'
        
        # Integer fields don't change but get flagged
        assert filtered['total_endpoints'] == 10
        assert len(flags) >= 2


class TestValidateEnums:
    """Tests for validate_enums function."""
    
    def test_valid_enums(self):
        """Test validation passes for valid enum values."""
        metadata = {
            'auth_required': 'yes',
            'schema_depth': 'medium',
            'parameter_complexity': 'low',
            'pagination_pattern': 'offset_limit'
        }
        
        errors = validate_enums(metadata)
        
        assert len(errors) == 0
    
    def test_invalid_enum(self):
        """Test validation catches invalid enum values."""
        metadata = {
            'auth_required': 'maybe',  # Invalid
            'schema_depth': 'very_deep'  # Invalid
        }
        
        errors = validate_enums(metadata)
        
        assert len(errors) > 0
        assert any('auth_required' in error for error in errors)


class TestValidateAndMerge:
    """Tests for validate_and_merge orchestration function."""
    
    def test_complete_flow(self):
        """Test complete validation and merging flow."""
        programmatic = {
            'avg_response_size_kb': 15.0,
            'schema_depth': 'shallow',
            'pagination_supported': False,
            'pagination_pattern': 'none',
            'rate_limiting': 'none',
            'auth_detected': False
        }
        
        llm = LLMAnalysisResult(
            total_endpoints=5,
            auth_required='no',
            parameter_complexity='low',
            error_surface='low',
            error_codes_count=3,
            doc_coverage='medium',
            reasoning={
                'total_endpoints': 'Found 5 endpoints',
                'auth_required': 'No auth needed',
                'parameter_complexity': 'Simple params',
                'error_surface': 'Basic errors',
                'error_codes_count': '3 codes',
                'doc_coverage': 'Decent docs'
            },
            confidence={
                'total_endpoints': 0.9,
                'auth_required': 0.95,
                'parameter_complexity': 0.85,
                'error_surface': 0.8,
                'error_codes_count': 0.9,
                'doc_coverage': 0.75
            }
        )
        
        result = validate_and_merge(
            api_name="Test API",
            programmatic=programmatic,
            llm=llm,
            confidence_threshold=0.7
        )
        
        assert isinstance(result, AnalysisResult)
        assert result.metadata.service_name == "Test API"
        assert result.metadata.total_endpoints == 5
        assert result.source == 'merged'
        assert result.average_confidence > 0.8


class TestYAMLGeneration:
    """Tests for YAML generation."""
    
    def test_generate_yaml_entry(self):
        """Test generating YAML entry for single API."""
        metadata = APIMetadata(
            service_name="Test API",
            total_endpoints=10,
            auth_required='yes',
            pagination_supported=True,
            schema_depth='medium',
            avg_response_size_kb=12.5,
            error_surface='medium',
            parameter_complexity='low',
            pagination_pattern='cursor',
            rate_limiting='simple',
            doc_coverage='high',
            error_codes_count=5
        )
        
        yaml_str = generate_yaml_entry("Test API", metadata)
        
        assert 'Test API' in yaml_str
        assert 'total_endpoints: 10' in yaml_str or 'total_endpoints:\n  10' in yaml_str
    
    def test_generate_yaml_file(self, tmp_path):
        """Test generating complete YAML file."""
        metadata1 = APIMetadata(
            service_name="API A",
            total_endpoints=5,
            auth_required='no',
            pagination_supported=False,
            schema_depth='shallow',
            avg_response_size_kb=5.0,
            error_surface='low',
            parameter_complexity='low',
            pagination_pattern='none',
            rate_limiting='none',
            doc_coverage='medium',
            error_codes_count=2
        )
        
        result1 = AnalysisResult(
            metadata=metadata1,
            confidence_scores={},
            reasoning={},
            flags=[],
            source='merged'
        )
        
        output_path = tmp_path / "test_output.yaml"
        generate_yaml_file([result1], str(output_path))
        
        assert output_path.exists()
        content = output_path.read_text()
        assert 'API A' in content
        assert 'Generated:' in content  # Check for header
