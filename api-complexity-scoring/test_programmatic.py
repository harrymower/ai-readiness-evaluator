#!/usr/bin/env python3
"""
Test script for programmatic API analyzer.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api_analysis.analyzers.programmatic import (
    analyze_api_programmatically,
    calculate_json_depth,
    classify_depth,
    detect_pagination,
    detect_rate_limiting,
)

print("=" * 70)
print("Testing Programmatic API Analyzer")
print("=" * 70)

# Test 1: JSON depth calculation
print("\n1. Testing JSON depth calculation...")
test_cases = [
    ({'a': 1}, 1, 'shallow'),
    ({'a': {'b': 2}}, 2, 'shallow'),
    ({'a': {'b': {'c': 3}}}, 3, 'medium'),
    ({'a': {'b': {'c': {'d': {'e': 5}}}}}, 5, 'deep'),
    ([1, 2, 3], 1, 'shallow'),
    ([{'a': {'b': 2}}], 3, 'medium'),
]

for obj, expected_depth, expected_class in test_cases:
    depth = calculate_json_depth(obj)
    depth_class = classify_depth(depth)
    status = "✓" if depth == expected_depth and depth_class == expected_class else "✗"
    print(f"   {status} Structure: {str(obj)[:50]:<50} Depth: {depth} ({depth_class})")

# Test 2: Pagination detection
print("\n2. Testing pagination detection...")
pagination_tests = [
    ({'next': 'url', 'offset': 0, 'limit': 20}, 'offset_limit'),
    ({'cursor': 'abc123', 'next_cursor': 'def456'}, 'cursor'),
    ({'page': 1, 'per_page': 20, 'total': 100}, 'page_size'),
    ({'next': 'url'}, 'other'),
    ({'data': [1, 2, 3]}, 'none'),
]

for obj, expected_pattern in pagination_tests:
    result = detect_pagination(obj, {})
    status = "✓" if result['pattern'] == expected_pattern else "✗"
    print(f"   {status} Pattern: {expected_pattern:<15} Detected: {result['pattern']}")

# Test 3: Rate limiting detection
print("\n3. Testing rate limiting detection...")
rate_limit_tests = [
    ({'X-RateLimit-Limit': '60', 'X-RateLimit-Remaining': '59'}, 'simple'),
    ({'X-RateLimit-Limit': '60', 'X-RateLimit-Remaining': '59', 'X-RateLimit-Reset': '123'}, 'complex'),
    ({'Content-Type': 'application/json'}, 'none'),
]

for headers, expected in rate_limit_tests:
    result = detect_rate_limiting(headers)
    status = "✓" if result['complexity'] == expected else "✗"
    print(f"   {status} Expected: {expected:<10} Got: {result['complexity']}")

# Test 4: Real API analysis
print("\n4. Testing real API analysis...")
print("   Testing with GitHub API...")

result = analyze_api_programmatically('curl https://api.github.com/users/octocat')

if result['error']:
    print(f"   ✗ Request failed: {result['error']}")
else:
    print(f"   ✓ Status: {result['status_code']}")
    print(f"   ✓ Response size: {result['avg_response_size_kb']} KB")
    print(f"   ✓ Schema depth: {result['schema_depth']}")
    print(f"   ✓ Pagination: {result['pagination_supported']} ({result['pagination_pattern']})")
    print(f"   ✓ Rate limiting: {result['rate_limiting']}")
    print(f"   ✓ Auth detected: {result['auth_detected']}")

print("\n" + "=" * 70)
print("Programmatic analyzer tests complete!")
print("=" * 70)
