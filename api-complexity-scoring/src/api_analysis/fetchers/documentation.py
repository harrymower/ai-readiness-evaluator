"""
Documentation fetching and cleaning for API analysis.

This module fetches API documentation from URLs and extracts clean text content
for LLM consumption. Supports various documentation formats including Swagger UI,
ReadTheDocs, GitHub Pages, and plain HTML.
"""

import re
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def fetch_documentation(url: str, timeout: int = 30) -> Dict:
    """
    Fetch HTML content from URL.
    
    Args:
        url: Documentation URL to fetch
        timeout: Request timeout in seconds (default: 30)
        
    Returns:
        Dict with: status_code, html, error
        
    Example:
        >>> result = fetch_documentation('https://petstore.swagger.io/')
        >>> result['status_code']
        200
    """
    try:
        # Set User-Agent to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                         '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Fetch with redirects enabled
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True
        )
        
        response.raise_for_status()
        
        return {
            'status_code': response.status_code,
            'html': response.text,
            'error': None
        }
        
    except requests.exceptions.Timeout:
        return {
            'status_code': None,
            'html': '',
            'error': f'Request timeout after {timeout} seconds'
        }
    except requests.exceptions.ConnectionError as e:
        return {
            'status_code': None,
            'html': '',
            'error': f'Connection error: {str(e)}'
        }
    except requests.exceptions.HTTPError as e:
        return {
            'status_code': e.response.status_code if e.response else None,
            'html': '',
            'error': f'HTTP error: {str(e)}'
        }
    except Exception as e:
        return {
            'status_code': None,
            'html': '',
            'error': f'Unexpected error: {str(e)}'
        }


def clean_html(html: str, max_length: int = 1_000_000) -> str:
    """
    Parse HTML and extract clean text content.
    
    Removes scripts, styles, navigation, footers, and extracts main content.
    Preserves structure with headings, lists, and code blocks.
    
    Args:
        html: Raw HTML content
        max_length: Maximum content length (default: 1MB)
        
    Returns:
        Clean text content
        
    Example:
        >>> html = '<html><body><h1>API</h1><p>Docs</p></body></html>'
        >>> clean_html(html)
        'API\\n\\nDocs'
    """
    if not html:
        return ''
    
    try:
        # Parse HTML
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove unwanted tags
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
            tag.decompose()
        
        # Try to find main content area
        main_content = None
        
        # Common main content selectors
        for selector in ['main', 'article', '[role="main"]', '.content', '#content', 
                        '.documentation', '.main-content']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # If no main content found, use body
        if not main_content:
            main_content = soup.body if soup.body else soup
        
        # Extract text with structure
        text_parts = []
        
        for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 
                                              'li', 'pre', 'code', 'div']):
            text = element.get_text(strip=True)
            if text:
                # Add extra newline before headings
                if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    text_parts.append(f'\n{text}\n')
                # Preserve code blocks
                elif element.name in ['pre', 'code']:
                    text_parts.append(f'```\n{text}\n```')
                else:
                    text_parts.append(text)
        
        # Join and clean up
        content = '\n'.join(text_parts)
        
        # Remove excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        
        # Truncate if too long
        if len(content) > max_length:
            # Try to truncate at sentence boundary
            truncated = content[:max_length]
            last_period = truncated.rfind('.')
            if last_period > max_length * 0.9:  # Only if close to end
                content = truncated[:last_period + 1]
            else:
                content = truncated
            content += '\n\n[Content truncated due to length]'
        
        return content
        
    except Exception as e:
        # Return empty string on parsing errors
        return f'Error parsing HTML: {str(e)}'


def detect_documentation_type(html: str) -> str:
    """
    Detect the type of documentation from HTML content.
    
    Args:
        html: HTML content
        
    Returns:
        Documentation type: 'swagger_ui', 'readthedocs', 'github_pages', 
        'markdown', or 'html'
        
    Example:
        >>> html = '<div class="swagger-ui"></div>'
        >>> detect_documentation_type(html)
        'swagger_ui'
    """
    if not html:
        return 'html'
    
    html_lower = html.lower()
    
    # Check for Swagger UI
    if 'swagger-ui' in html_lower or 'swagger ui' in html_lower:
        return 'swagger_ui'
    
    # Check for ReadTheDocs
    if 'readthedocs' in html_lower or 'class="rst-' in html_lower:
        return 'readthedocs'
    
    # Check for GitHub Pages
    if 'github.io' in html_lower or 'class="markdown-body"' in html_lower:
        return 'github_pages'
    
    # Check for common documentation frameworks
    if 'docsify' in html_lower or 'gitbook' in html_lower:
        return 'markdown'
    
    return 'html'


def extract_openapi_spec_url(html: str, base_url: str) -> Optional[str]:
    """
    Extract OpenAPI/Swagger spec URL from HTML.
    
    Looks for links to .json or .yaml files and common spec paths.
    
    Args:
        html: HTML content
        base_url: Base URL for resolving relative paths
        
    Returns:
        Absolute URL to spec file, or None if not found
        
    Example:
        >>> html = '<script>SwaggerUIBundle({url: "/openapi.json"})</script>'
        >>> extract_openapi_spec_url(html, 'https://api.example.com')
        'https://api.example.com/openapi.json'
    """
    if not html:
        return None
    
    try:
        # Parse base URL for joining
        parsed_base = urlparse(base_url)
        base_scheme = parsed_base.scheme
        base_netloc = parsed_base.netloc
        
        # Common spec paths to check
        common_paths = [
            '/openapi.json', '/openapi.yaml', '/openapi.yml',
            '/swagger.json', '/swagger.yaml', '/swagger.yml',
            '/api-docs', '/api-docs.json', '/api-docs.yaml',
            '/v2/api-docs', '/v3/api-docs',
            '/docs/openapi.json', '/docs/swagger.json',
        ]
        
        # Check if any common paths are in the HTML
        for path in common_paths:
            if path in html.lower():
                return urljoin(base_url, path)
        
        # Parse HTML to find links
        soup = BeautifulSoup(html, 'lxml')
        
        # Look for links to spec files
        for link in soup.find_all(['a', 'link']):
            href = link.get('href', '')
            if href and (
                href.endswith('.json') or 
                href.endswith('.yaml') or 
                href.endswith('.yml')
            ):
                # Check if it looks like an OpenAPI/Swagger spec
                href_lower = href.lower()
                if any(keyword in href_lower for keyword in 
                       ['openapi', 'swagger', 'api-docs', 'spec']):
                    return urljoin(base_url, href)
        
        # Look for Swagger UI initialization in scripts
        for script in soup.find_all('script'):
            script_text = script.get_text()
            # Look for SwaggerUIBundle or similar with url parameter
            url_match = re.search(r'["\']url["\']\s*:\s*["\']([^"\']+)["\']', script_text)
            if url_match:
                spec_url = url_match.group(1)
                return urljoin(base_url, spec_url)
        
        return None
        
    except Exception:
        return None


def fetch_and_clean_documentation(url: str, timeout: int = 30) -> Dict:
    """
    Main orchestration function to fetch, detect, and clean documentation.
    
    Args:
        url: Documentation URL
        timeout: Request timeout in seconds
        
    Returns:
        Dict with:
        - content: Cleaned text content
        - type: Documentation type
        - openapi_url: OpenAPI spec URL (if found)
        - error: Error message (if any)
        
    Example:
        >>> result = fetch_and_clean_documentation('https://petstore.swagger.io/')
        >>> result['type']
        'swagger_ui'
        >>> result['openapi_url']
        'https://petstore.swagger.io/v2/swagger.json'
    """
    # Fetch HTML
    fetch_result = fetch_documentation(url, timeout)
    
    if fetch_result['error']:
        return {
            'content': '',
            'type': 'unknown',
            'openapi_url': None,
            'error': fetch_result['error']
        }
    
    html = fetch_result['html']
    
    # Detect documentation type
    doc_type = detect_documentation_type(html)
    
    # Clean HTML to text
    content = clean_html(html)
    
    # Extract OpenAPI spec URL
    openapi_url = extract_openapi_spec_url(html, url)
    
    return {
        'content': content,
        'type': doc_type,
        'openapi_url': openapi_url,
        'error': None
    }
