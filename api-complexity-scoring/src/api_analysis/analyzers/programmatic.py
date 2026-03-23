"""
Programmatic API analysis - Stage 1.

This module extracts objective metrics from API responses without using LLMs.
Analyzes: response size, schema depth, pagination, rate limiting, etc.
"""

import json
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


def execute_curl(curl_command: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute a curl command and return response data.
    
    Args:
        curl_command: Complete curl command string
        timeout: Timeout in seconds
        
    Returns:
        Dict with: status_code, headers, body, size_bytes, error
        
    Example:
        >>> result = execute_curl('curl https://api.github.com')
        >>> result['status_code']
        200
    """
    try:
        # Add flags to get headers and follow redirects
        if '-i' not in curl_command and '--include' not in curl_command:
            curl_command = curl_command.replace('curl ', 'curl -i ')
        
        # Add timeout
        if '-m' not in curl_command and '--max-time' not in curl_command:
            curl_command += f' -m {timeout}'
        
        # Execute curl command
        result = subprocess.run(
            curl_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout
        
        # Parse response
        if not output:
            return {
                'status_code': None,
                'headers': {},
                'body': '',
                'size_bytes': 0,
                'error': result.stderr or 'No response received'
            }
        
        # Split headers and body
        parts = output.split('\r\n\r\n', 1)
        if len(parts) < 2:
            parts = output.split('\n\n', 1)
        
        if len(parts) >= 2:
            header_section = parts[0]
            body = parts[1]
        else:
            header_section = ''
            body = output
        
        # Parse status code
        status_code = None
        status_match = re.search(r'HTTP/[\d.]+\s+(\d+)', header_section)
        if status_match:
            status_code = int(status_match.group(1))
        
        # Parse headers
        headers = {}
        for line in header_section.split('\n'):
            if ':' in line and not line.startswith('HTTP/'):
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()
        
        # Calculate size
        size_bytes = len(body.encode('utf-8'))
        
        return {
            'status_code': status_code,
            'headers': headers,
            'body': body,
            'size_bytes': size_bytes,
            'error': None
        }
        
    except subprocess.TimeoutExpired:
        return {
            'status_code': None,
            'headers': {},
            'body': '',
            'size_bytes': 0,
            'error': f'Request timeout after {timeout} seconds'
        }
    except Exception as e:
        return {
            'status_code': None,
            'headers': {},
            'body': '',
            'size_bytes': 0,
            'error': str(e)
        }


def calculate_json_depth(json_obj: Any, current_depth: int = 0) -> int:
    """
    Recursively calculate the maximum nesting depth of a JSON object.
    
    Args:
        json_obj: JSON object (dict, list, or primitive)
        current_depth: Current recursion depth
        
    Returns:
        Maximum depth of nesting
        
    Example:
        >>> calculate_json_depth({'a': {'b': {'c': 1}}})
        3
        >>> calculate_json_depth([1, 2, 3])
        1
    """
    if not isinstance(json_obj, (dict, list)):
        return current_depth
    
    if isinstance(json_obj, dict):
        if not json_obj:
            return current_depth + 1
        return max(
            calculate_json_depth(v, current_depth + 1)
            for v in json_obj.values()
        )
    
    if isinstance(json_obj, list):
        if not json_obj:
            return current_depth + 1
        return max(
            calculate_json_depth(item, current_depth + 1)
            for item in json_obj
        )
    
    return current_depth


def classify_depth(depth: int) -> str:
    """
    Classify JSON depth into categories.
    
    Args:
        depth: Nesting depth (0+)
        
    Returns:
        'shallow' (≤2), 'medium' (3-4), or 'deep' (≥5)
        
    Example:
        >>> classify_depth(2)
        'shallow'
        >>> classify_depth(4)
        'medium'
        >>> classify_depth(6)
        'deep'
    """
    if depth <= 2:
        return 'shallow'
    elif depth <= 4:
        return 'medium'
    else:
        return 'deep'


def detect_pagination(json_obj: Any, headers: Dict[str, str]) -> Dict[str, Any]:
    """
    Detect pagination support and pattern from response.
    
    Checks for common pagination fields and patterns:
    - Cursor-based: 'cursor', 'next_cursor', 'before', 'after'
    - Offset/limit: 'offset', 'limit', 'skip', 'take'
    - Page-based: 'page', 'per_page', 'page_size'
    - Link headers (RFC 5988)
    
    Args:
        json_obj: Parsed JSON response
        headers: Response headers
        
    Returns:
        Dict with 'supported' (bool) and 'pattern' (str)
        
    Example:
        >>> detect_pagination({'next': 'url', 'offset': 0, 'limit': 20}, {})
        {'supported': True, 'pattern': 'offset_limit'}
    """
    if not json_obj:
        return {'supported': False, 'pattern': 'none'}
    
    # Check for Link header (common in REST APIs)
    if 'Link' in headers or 'link' in headers:
        return {'supported': True, 'pattern': 'cursor'}
    
    # Flatten JSON to check all keys
    def get_all_keys(obj: Any) -> List[str]:
        keys = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                keys.append(k.lower())
                keys.extend(get_all_keys(v))
        elif isinstance(obj, list) and obj:
            keys.extend(get_all_keys(obj[0]))
        return keys
    
    all_keys = set(get_all_keys(json_obj))
    
    # Cursor-based pagination
    cursor_fields = {'cursor', 'next_cursor', 'previous_cursor', 'before', 'after', 
                     'continuation_token', 'next_token'}
    if any(field in all_keys for field in cursor_fields):
        return {'supported': True, 'pattern': 'cursor'}
    
    # Offset/limit pagination
    offset_fields = {'offset', 'skip'}
    limit_fields = {'limit', 'take', 'count', 'size'}
    if (any(field in all_keys for field in offset_fields) and 
        any(field in all_keys for field in limit_fields)):
        return {'supported': True, 'pattern': 'offset_limit'}
    
    # Page-based pagination
    page_fields = {'page', 'page_number', 'current_page'}
    per_page_fields = {'per_page', 'page_size', 'items_per_page'}
    if (any(field in all_keys for field in page_fields) and 
        any(field in all_keys for field in per_page_fields)):
        return {'supported': True, 'pattern': 'page_size'}
    
    # Check for just 'next' or 'prev' links (common pattern)
    next_prev_fields = {'next', 'previous', 'prev', 'next_page', 'prev_page'}
    if any(field in all_keys for field in next_prev_fields):
        return {'supported': True, 'pattern': 'other'}
    
    return {'supported': False, 'pattern': 'none'}


def detect_rate_limiting(headers: Dict[str, str]) -> Dict[str, Any]:
    """
    Detect rate limiting from response headers.
    
    Checks for common rate limit headers:
    - X-RateLimit-*
    - RateLimit-*
    - X-Rate-Limit-*
    - Retry-After
    
    Args:
        headers: Response headers (case-insensitive)
        
    Returns:
        Dict with 'detected' (bool) and 'complexity' (str)
        Complexity: 'none', 'simple' (basic limit), 'complex' (multiple tiers)
        
    Example:
        >>> detect_rate_limiting({'X-RateLimit-Limit': '60'})
        {'detected': True, 'complexity': 'simple'}
    """
    # Normalize header keys to lowercase
    normalized_headers = {k.lower(): v for k, v in headers.items()}
    
    rate_limit_patterns = [
        'x-ratelimit-', 'ratelimit-', 'x-rate-limit-', 'retry-after'
    ]
    
    rate_limit_headers = []
    for header_key in normalized_headers.keys():
        if any(pattern in header_key for pattern in rate_limit_patterns):
            rate_limit_headers.append(header_key)
    
    if not rate_limit_headers:
        return {'detected': False, 'complexity': 'none'}
    
    # Determine complexity based on number of rate limit headers
    # Simple: Just basic limit (1-2 headers)
    # Complex: Multiple tiers, windows, or quotas (3+ headers)
    if len(rate_limit_headers) >= 3:
        return {'detected': True, 'complexity': 'complex'}
    else:
        return {'detected': True, 'complexity': 'simple'}


def analyze_api_programmatically(
    curl_command: str,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Main function to analyze an API programmatically.
    
    Executes the curl command and extracts all objective metrics:
    - Response size
    - Schema depth
    - Pagination support and pattern
    - Rate limiting detection
    - Authentication detection
    
    Args:
        curl_command: Complete curl command
        timeout: Request timeout in seconds
        
    Returns:
        Dict with all programmatic analysis results
        
    Example:
        >>> result = analyze_api_programmatically('curl https://api.github.com/users')
        >>> result['schema_depth']
        'shallow'
    """
    # Execute request
    response = execute_curl(curl_command, timeout)
    
    # Initialize results
    results = {
        'status_code': response['status_code'],
        'avg_response_size_kb': round(response['size_bytes'] / 1024, 2) if response['size_bytes'] else 0,
        'schema_depth': 'unknown',
        'pagination_supported': False,
        'pagination_pattern': 'none',
        'rate_limiting': 'none',
        'auth_detected': False,
        'error': response['error']
    }
    
    # If request failed, return early
    if response['error'] or not response['body']:
        return results
    
    # Try to parse JSON
    try:
        json_data = json.loads(response['body'])
        
        # Calculate schema depth
        depth = calculate_json_depth(json_data)
        results['schema_depth'] = classify_depth(depth)
        
        # Detect pagination
        pagination = detect_pagination(json_data, response['headers'])
        results['pagination_supported'] = pagination['supported']
        results['pagination_pattern'] = pagination['pattern']
        
    except json.JSONDecodeError:
        # Not JSON, skip JSON-based analysis
        results['schema_depth'] = 'unknown'
    
    # Detect rate limiting
    rate_limit = detect_rate_limiting(response['headers'])
    if rate_limit['detected']:
        results['rate_limiting'] = rate_limit['complexity']
    
    # Detect authentication requirement
    # Check for auth headers in request or 401/403 status
    if 'authorization' in curl_command.lower() or 'x-api-key' in curl_command.lower():
        results['auth_detected'] = True
    elif response['status_code'] in [401, 403]:
        results['auth_detected'] = True
    
    # Check for WWW-Authenticate header
    auth_headers = ['www-authenticate', 'authorization', 'x-api-key']
    if any(header in [k.lower() for k in response['headers'].keys()] for header in auth_headers):
        results['auth_detected'] = True
    
    return results


def analyze_multiple_endpoints(
    curl_commands: List[str],
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Analyze multiple API endpoints and aggregate results.
    
    Args:
        curl_commands: List of curl commands
        timeout: Request timeout in seconds
        
    Returns:
        Dict with aggregated metrics
    """
    if not curl_commands:
        return {}
    
    results = []
    for cmd in curl_commands:
        result = analyze_api_programmatically(cmd, timeout)
        if not result['error']:
            results.append(result)
    
    if not results:
        return {'error': 'All requests failed'}
    
    # Aggregate results
    total_endpoints = len(results)
    avg_size = sum(r['avg_response_size_kb'] for r in results) / total_endpoints
    
    # Most common depth
    depths = [r['schema_depth'] for r in results if r['schema_depth'] != 'unknown']
    most_common_depth = max(set(depths), key=depths.count) if depths else 'unknown'
    
    # Any pagination?
    any_pagination = any(r['pagination_supported'] for r in results)
    
    # Most common pagination pattern
    patterns = [r['pagination_pattern'] for r in results if r['pagination_pattern'] != 'none']
    most_common_pattern = max(set(patterns), key=patterns.count) if patterns else 'none'
    
    # Most complex rate limiting
    rate_limits = [r['rate_limiting'] for r in results]
    if 'complex' in rate_limits:
        rate_limiting = 'complex'
    elif 'simple' in rate_limits:
        rate_limiting = 'simple'
    else:
        rate_limiting = 'none'
    
    # Any auth required?
    any_auth = any(r['auth_detected'] for r in results)
    
    return {
        'total_endpoints': total_endpoints,
        'avg_response_size_kb': round(avg_size, 2),
        'schema_depth': most_common_depth,
        'pagination_supported': any_pagination,
        'pagination_pattern': most_common_pattern,
        'rate_limiting': rate_limiting,
        'auth_required': 'yes' if any_auth else 'no',
    }
