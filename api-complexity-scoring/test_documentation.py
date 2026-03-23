"""
Tests for documentation fetching and cleaning.

Unit tests for HTML fetching, cleaning, type detection, and OpenAPI spec extraction.
"""

import pytest
from unittest.mock import Mock, patch

from api_analysis.fetchers.documentation import (
    fetch_documentation,
    clean_html,
    detect_documentation_type,
    extract_openapi_spec_url,
    fetch_and_clean_documentation
)


class TestFetchDocumentation:
    """Tests for fetch_documentation function."""
    
    @patch('api_analysis.fetchers.documentation.requests.get')
    def test_successful_fetch(self, mock_get):
        """Test successful HTML fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Test</body></html>'
        mock_get.return_value = mock_response
        
        result = fetch_documentation('https://example.com')
        
        assert result['status_code'] == 200
        assert result['html'] == '<html><body>Test</body></html>'
        assert result['error'] is None
    
    @patch('api_analysis.fetchers.documentation.requests.get')
    def test_timeout(self, mock_get):
        """Test timeout handling."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        result = fetch_documentation('https://example.com', timeout=5)
        
        assert result['status_code'] is None
        assert 'timeout' in result['error'].lower()
    
    @patch('api_analysis.fetchers.documentation.requests.get')
    def test_http_error(self, mock_get):
        """Test HTTP error handling."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_get.return_value = mock_response
        
        result = fetch_documentation('https://example.com')
        
        assert result['status_code'] == 404
        assert result['error'] is not None


class TestCleanHTML:
    """Tests for clean_html function."""
    
    def test_basic_cleaning(self):
        """Test basic HTML cleaning."""
        html = '<html><body><h1>Title</h1><p>Content</p></body></html>'
        result = clean_html(html)
        
        assert 'Title' in result
        assert 'Content' in result
    
    def test_remove_scripts(self):
        """Test script removal."""
        html = '<html><body><script>alert("test")</script><p>Content</p></body></html>'
        result = clean_html(html)
        
        assert 'alert' not in result
        assert 'Content' in result
    
    def test_remove_styles(self):
        """Test style removal."""
        html = '<html><head><style>body{color:red}</style></head><body><p>Content</p></body></html>'
        result = clean_html(html)
        
        assert 'color:red' not in result
        assert 'Content' in result
    
    def test_truncate_long_content(self):
        """Test content truncation for long HTML."""
        long_content = 'x' * 2_000_000
        html = f'<html><body><p>{long_content}</p></body></html>'
        result = clean_html(html, max_length=1000)
        
        assert len(result) <= 1100  # Allow some overhead for truncation message
        assert 'truncated' in result.lower()


class TestDetectDocumentationType:
    """Tests for detect_documentation_type function."""
    
    def test_swagger_ui(self):
        """Test Swagger UI detection."""
        html = '<html><div class="swagger-ui"></div></html>'
        assert detect_documentation_type(html) == 'swagger_ui'
    
    def test_readthedocs(self):
        """Test ReadTheDocs detection."""
        html = '<html><div class="rst-content"></div></html>'
        assert detect_documentation_type(html) == 'readthedocs'
    
    def test_github_pages(self):
        """Test GitHub Pages detection."""
        html = '<html><div class="markdown-body"></div></html>'
        assert detect_documentation_type(html) == 'github_pages'
    
    def test_unknown_html(self):
        """Test generic HTML."""
        html = '<html><body>Content</body></html>'
        assert detect_documentation_type(html) == 'html'


class TestExtractOpenAPISpecURL:
    """Tests for extract_openapi_spec_url function."""
    
    def test_extract_from_common_path(self):
        """Test extraction from common OpenAPI paths."""
        html = '<a href="/openapi.json">API Spec</a>'
        result = extract_openapi_spec_url(html, 'https://api.example.com')
        
        assert result == 'https://api.example.com/openapi.json'
    
    def test_extract_from_swagger_ui_script(self):
        """Test extraction from Swagger UI initialization."""
        html = '<script>SwaggerUIBundle({url: "/v2/api-docs"})</script>'
        result = extract_openapi_spec_url(html, 'https://api.example.com')
        
        assert '/api-docs' in result or 'v2' in result
    
    def test_no_spec_found(self):
        """Test when no spec is found."""
        html = '<html><body>No spec here</body></html>'
        result = extract_openapi_spec_url(html, 'https://api.example.com')
        
        assert result is None


class TestFetchAndCleanDocumentation:
    """Tests for fetch_and_clean_documentation orchestration function."""
    
    @patch('api_analysis.fetchers.documentation.fetch_documentation')
    def test_successful_flow(self, mock_fetch):
        """Test complete successful flow."""
        mock_fetch.return_value = {
            'status_code': 200,
            'html': '<html><div class="swagger-ui"></div><a href="/openapi.json">spec</a></html>',
            'error': None
        }
        
        result = fetch_and_clean_documentation('https://example.com')
        
        assert result['type'] == 'swagger_ui'
        assert result['openapi_url'] is not None
        assert result['error'] is None
    
    @patch('api_analysis.fetchers.documentation.fetch_documentation')
    def test_fetch_error(self, mock_fetch):
        """Test handling of fetch errors."""
        mock_fetch.return_value = {
            'status_code': None,
            'html': '',
            'error': 'Connection failed'
        }
        
        result = fetch_and_clean_documentation('https://example.com')
        
        assert result['error'] == 'Connection failed'
        assert result['content'] == ''


# Integration tests (require actual network access)
class TestIntegration:
    """Integration tests with real URLs."""
    
    @pytest.mark.skip(reason="Requires network access, enable manually if needed")
    def test_fetch_real_swagger_ui(self):
        """Test fetching from real Swagger UI page."""
        result = fetch_and_clean_documentation('https://petstore.swagger.io/')
        
        assert result['type'] == 'swagger_ui'
        assert result['error'] is None
        assert len(result['content']) > 0
