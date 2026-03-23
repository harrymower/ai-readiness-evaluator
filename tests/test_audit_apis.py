"""
Unit tests for scripts/audit_apis.py complexity scoring functionality.
"""

import sys
from pathlib import Path

# Add parent directory to path to import audit_apis module
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.audit_apis import calculate_complexity_score


class TestCalculateComplexityScore:
    """Test cases for the calculate_complexity_score function."""

    def test_simple_api_minimal_complexity(self):
        """Test scoring for a very simple API (e.g., Ipify)."""
        metadata = {
            'auth_required': 'no',
            'total_endpoints': 1,
            'schema_depth': 'shallow',
            'avg_response_size_kb': 0.1,
            'error_surface': 'low',
            'error_codes_count': 1,
            'pagination_supported': 'no',
            'pagination_pattern': 'none',
            'parameter_complexity': 'low',
            'rate_limiting': 'none',
            'doc_coverage': 'low'
        }
        
        result = calculate_complexity_score(metadata)
        
        # RCS = 0+0+0+0+0+0+0+0+0+0 = 0
        # ECS = 0 + 1 (low docs) = 1
        # Score = (1/20) * 10 = 0.5
        assert result['raw_structural_score'] == 0
        assert result['effective_score'] == 1
        assert result['complexity_score_0_10'] == 0.5
        assert result['complexity_bucket'] == 'Simple'

    def test_moderate_api(self):
        """Test scoring for a moderate complexity API (e.g., Jikan)."""
        metadata = {
            'auth_required': 'no',
            'total_endpoints': 20,
            'schema_depth': 'deep',
            'avg_response_size_kb': 15,
            'error_surface': 'medium',
            'error_codes_count': 5,
            'pagination_supported': 'yes',
            'pagination_pattern': 'page_size',
            'parameter_complexity': 'medium',
            'rate_limiting': 'simple',
            'doc_coverage': 'medium'
        }
        
        result = calculate_complexity_score(metadata)
        
        # RCS = 0+1+2+1+1+1+1+1+1+1 = 10
        # ECS = 10 + 0 (medium docs) = 10
        # Score = (10/20) * 10 = 5.0
        assert result['raw_structural_score'] == 10
        assert result['effective_score'] == 10
        assert result['complexity_score_0_10'] == 5.0
        assert result['complexity_bucket'] == 'Moderate'

    def test_complex_api(self):
        """Test scoring for a complex API (e.g., GitHub)."""
        metadata = {
            'auth_required': 'optional',
            'total_endpoints': 200,
            'schema_depth': 'medium',
            'avg_response_size_kb': 5,
            'error_surface': 'high',
            'error_codes_count': 12,
            'pagination_supported': 'yes',
            'pagination_pattern': 'mixed',
            'parameter_complexity': 'high',
            'rate_limiting': 'complex',
            'doc_coverage': 'high'
        }
        
        result = calculate_complexity_score(metadata)
        
        # RCS = 1+3+1+0+2+2+1+2+2+2 = 16
        # ECS = 16 - 1 (high docs) = 15
        # Score = (15/20) * 10 = 7.5
        assert result['raw_structural_score'] == 16
        assert result['effective_score'] == 15
        assert result['complexity_score_0_10'] == 7.5
        assert result['complexity_bucket'] == 'Complex'

    def test_very_complex_api(self):
        """Test scoring for a very complex API (e.g., Spoonacular)."""
        metadata = {
            'auth_required': 'yes',
            'total_endpoints': 80,
            'schema_depth': 'deep',
            'avg_response_size_kb': 25,
            'error_surface': 'high',
            'error_codes_count': 10,
            'pagination_supported': 'yes',
            'pagination_pattern': 'offset_limit',
            'parameter_complexity': 'high',
            'rate_limiting': 'complex',
            'doc_coverage': 'high'
        }
        
        result = calculate_complexity_score(metadata)
        
        # RCS = 2+2+2+1+2+2+1+1+2+2 = 17
        # ECS = 17 - 1 (high docs) = 16
        # Score = (16/20) * 10 = 8.0
        assert result['raw_structural_score'] == 17
        assert result['effective_score'] == 16
        assert result['complexity_score_0_10'] == 8.0
        assert result['complexity_bucket'] == 'Very complex'

    def test_missing_fields_default_to_zero(self):
        """Test that missing/unknown fields default to zero contribution."""
        metadata = {
            'auth_required': 'unknown',
            'total_endpoints': 'unknown',
            'schema_depth': 'unknown',
            'avg_response_size_kb': 'unknown',
            'error_surface': 'unknown',
            'error_codes_count': 'unknown',
            'pagination_supported': 'unknown',
            'pagination_pattern': 'unknown',
            'parameter_complexity': 'unknown',
            'rate_limiting': 'unknown',
            'doc_coverage': 'unknown'
        }
        
        result = calculate_complexity_score(metadata)
        
        # All unknown should result in 0 score
        assert result['raw_structural_score'] == 0
        assert result['effective_score'] == 0
        assert result['complexity_score_0_10'] == 0.0
        assert result['complexity_bucket'] == 'Simple'

