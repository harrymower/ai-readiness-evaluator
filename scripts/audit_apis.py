#!/usr/bin/env python3
"""
API Audit Script for Phase 0.1

This script audits all APIs in config/apis.txt and gathers complexity signals
from config/api_metadata.yaml to generate docs/phase0_api_signals.md.

Complexity signals collected:
1. Auth present (Y/N)
2. Pagination (Y/N)
3. Endpoints count
4. Schema depth (shallow/medium/deep)
5. Average response size (KB)
6. Error surface (low/medium/high)
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any
import yaml

# Add parent directory to path to import ai_evaluator modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_evaluator.utils import parse_apis_config


def calculate_complexity_score(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate complexity score for an API service based on metadata.

    Returns a dict with:
    - raw_structural_score (RCS): Sum of all structural complexity signals
    - effective_score (ECS): RCS adjusted by documentation quality
    - complexity_score_0_10: Normalized score on 0-10 scale
    - complexity_bucket: Simple/Moderate/Complex/Very complex
    """

    # Initialize score
    score = 0

    # 1. auth_required: no→0, optional→1, yes→2, unknown→0
    auth_val = metadata.get('auth_required', 'unknown')
    if auth_val == 'yes' or auth_val is True:
        score += 2
    elif auth_val == 'optional':
        score += 1
    # else: no or unknown → 0

    # 2. total_endpoints: <=5→0, 6-20→1, 21-100→2, >100→3, unknown→0
    endpoints = metadata.get('total_endpoints', 0)
    if isinstance(endpoints, int):
        if endpoints <= 5:
            score += 0
        elif endpoints <= 20:
            score += 1
        elif endpoints <= 100:
            score += 2
        else:  # > 100
            score += 3
    # else: unknown → 0

    # 3. schema_depth: shallow→0, medium→1, deep→2, unknown→0
    schema_depth = metadata.get('schema_depth', 'unknown')
    if schema_depth == 'deep':
        score += 2
    elif schema_depth == 'medium':
        score += 1
    # else: shallow or unknown → 0

    # 4. avg_response_size_kb: <=5→0, 6-50→1, >50→2, unknown→0
    avg_size = metadata.get('avg_response_size_kb', 0)
    if isinstance(avg_size, (int, float)):
        if avg_size <= 5:
            score += 0
        elif avg_size <= 50:
            score += 1
        else:  # > 50
            score += 2
    # else: unknown → 0

    # 5. error_surface: low→0, medium→1, high→2, unknown→0
    error_surface = metadata.get('error_surface', 'unknown')
    if error_surface == 'high':
        score += 2
    elif error_surface == 'medium':
        score += 1
    # else: low or unknown → 0

    # 6. error_codes_count: 0-3→0, 4-7→1, >=8→2, unknown→0
    error_codes = metadata.get('error_codes_count', 0)
    if isinstance(error_codes, int):
        if error_codes >= 8:
            score += 2
        elif error_codes >= 4:
            score += 1
        # else: 0-3 → 0
    # else: unknown → 0

    # 7. pagination_supported: no→0, yes→1, unknown→0
    pagination_supported = metadata.get('pagination_supported', 'unknown')
    if pagination_supported == 'yes' or pagination_supported is True:
        score += 1
    # else: no or unknown → 0

    # 8. pagination_pattern: none→0, offset_limit/page_size→1, cursor/mixed/other→2, unknown→0
    pagination_pattern = metadata.get('pagination_pattern', 'unknown')
    if pagination_pattern in ['cursor', 'mixed', 'other']:
        score += 2
    elif pagination_pattern in ['offset_limit', 'page_size']:
        score += 1
    # else: none or unknown → 0

    # 9. parameter_complexity: low→0, medium→1, high→2, unknown→0
    param_complexity = metadata.get('parameter_complexity', 'unknown')
    if param_complexity == 'high':
        score += 2
    elif param_complexity == 'medium':
        score += 1
    # else: low or unknown → 0

    # 10. rate_limiting: none→0, simple→1, complex→2, unknown→0
    rate_limiting = metadata.get('rate_limiting', 'unknown')
    if rate_limiting == 'complex':
        score += 2
    elif rate_limiting == 'simple':
        score += 1
    # else: none or unknown → 0

    # Raw Structural Complexity Score (RCS)
    rcs = score

    # Documentation adjustment: high→-1, medium→0, low→+1, unknown→0
    doc_coverage = metadata.get('doc_coverage', 'unknown')
    doc_adjustment = 0
    if doc_coverage == 'high':
        doc_adjustment = -1
    elif doc_coverage == 'low':
        doc_adjustment = 1
    # else: medium or unknown → 0

    # Effective Complexity Score (ECS)
    ecs_raw = rcs + doc_adjustment
    ecs = max(0, ecs_raw)  # Clamp to non-negative

    # Normalize to 0-10 scale
    # Max possible RCS = 2+3+2+2+2+2+1+2+2+2 = 20
    complexity_score_0_10 = round((ecs / 20.0) * 10, 1)

    # Determine bucket
    if complexity_score_0_10 <= 2.5:
        bucket = 'Simple'
    elif complexity_score_0_10 <= 5.0:
        bucket = 'Moderate'
    elif complexity_score_0_10 <= 7.5:
        bucket = 'Complex'
    else:
        bucket = 'Very complex'

    return {
        'raw_structural_score': rcs,
        'effective_score': ecs,
        'complexity_score_0_10': complexity_score_0_10,
        'complexity_bucket': bucket
    }


def load_api_metadata(filepath: str = "config/api_metadata.yaml") -> Dict[str, Any]:
    """Load API metadata from YAML file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def extract_base_domain(url: str) -> str:
    """Extract base domain from a URL for matching with metadata."""
    # Remove protocol
    url = url.replace('https://', '').replace('http://', '')
    # Remove path
    url = url.split('/')[0]
    # Remove www. prefix if present
    url = url.replace('www.', '')
    # Remove api. prefix if present (e.g., api.github.com -> github.com)
    if url.startswith('api.'):
        url = url[4:]
    return url


def find_metadata_for_api(api_name: str, api_config: Dict[str, str], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Find metadata entry for a given API test scenario."""
    # First, check if this API name is directly listed in any metadata test_scenarios
    for meta_key, meta_value in metadata.items():
        if isinstance(meta_value, dict):
            test_scenarios = meta_value.get('test_scenarios', [])
            if api_name in test_scenarios:
                return meta_value

    # If not found by name, try to match by domain from curl command
    curl_cmd = api_config.get('curl_command', '')

    # Simple URL extraction from curl command
    for part in curl_cmd.split():
        if part.startswith('http'):
            url = part.strip('"\'')
            domain = extract_base_domain(url)

            # Try to find matching metadata entry
            for meta_key, meta_value in metadata.items():
                if domain == meta_key or domain in meta_key or meta_key in domain:
                    return meta_value

    return None


def generate_signals_table(apis: Dict[str, Dict[str, str]], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate table data with complexity signals for all APIs."""
    table_data = []

    for api_name, api_config in apis.items():
        meta = find_metadata_for_api(api_name, api_config, metadata)

        if meta:
            # Convert auth_required to Y/N/Optional
            auth_val = meta.get('auth_required', 'unknown')
            if auth_val is True or auth_val == 'yes':
                auth_display = 'Y'
            elif auth_val is False or auth_val == 'no':
                auth_display = 'N'
            elif auth_val == 'optional':
                auth_display = 'Optional'
            else:
                auth_display = 'unknown'

            # Convert pagination_supported to Y/N/unknown
            pagination_val = meta.get('pagination_supported', 'unknown')
            if pagination_val is True or pagination_val == 'yes':
                pagination_display = 'Y'
            elif pagination_val is False or pagination_val == 'no':
                pagination_display = 'N'
            else:
                pagination_display = 'unknown'

            # Calculate complexity score
            complexity_info = calculate_complexity_score(meta)

            row = {
                'api_name': api_name,
                'service_name': meta.get('service_name', 'unknown'),
                'auth_required': auth_display,
                'pagination': pagination_display,
                'endpoints_count': meta.get('total_endpoints', 'unknown'),
                'schema_depth': meta.get('schema_depth', 'unknown'),
                'avg_response_kb': meta.get('avg_response_size_kb', 'unknown'),
                'error_surface': meta.get('error_surface', 'unknown'),
                'complexity_score': complexity_info['complexity_score_0_10'],
                'complexity_bucket': complexity_info['complexity_bucket'],
                'notes': meta.get('notes', '')
            }
        else:
            # No metadata found
            row = {
                'api_name': api_name,
                'service_name': 'unknown',
                'auth_required': 'unknown',
                'pagination': 'unknown',
                'endpoints_count': 'unknown',
                'schema_depth': 'unknown',
                'avg_response_kb': 'unknown',
                'error_surface': 'unknown',
                'complexity_score': 0.0,
                'complexity_bucket': 'Simple',
                'notes': 'Metadata not found'
            }

        table_data.append(row)

    return table_data


def generate_markdown_report(table_data: List[Dict[str, Any]], output_path: str = "docs/phase0_api_signals.md") -> None:
    """Generate markdown report with API complexity signals."""

    # Ensure docs directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    from datetime import datetime

    md_content = []
    md_content.append("# Phase 0.1.0.1: API Complexity Signals with Scoring\n")
    md_content.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    md_content.append("**Generated by:** `scripts/audit_apis.py`\n")
    md_content.append("**Purpose:** Inventory all APIs and capture complexity signals for bucketing\n")
    md_content.append("\n## Summary\n")
    md_content.append(f"- **Total APIs audited:** {len(table_data)}\n")

    # Count by auth requirement
    auth_yes = sum(1 for row in table_data if row['auth_required'] == 'Y')
    auth_no = sum(1 for row in table_data if row['auth_required'] == 'N')
    auth_optional = sum(1 for row in table_data if row['auth_required'] == 'Optional')

    md_content.append(f"- **APIs requiring auth:** {auth_yes}\n")
    md_content.append(f"- **APIs without auth:** {auth_no}\n")
    md_content.append(f"- **APIs with optional auth:** {auth_optional}\n")

    # Count by pagination
    pagination_yes = sum(1 for row in table_data if row['pagination'] == 'Y')
    pagination_no = sum(1 for row in table_data if row['pagination'] == 'N')

    md_content.append(f"- **APIs with pagination:** {pagination_yes}\n")
    md_content.append(f"- **APIs without pagination:** {pagination_no}\n")

    # Count by complexity bucket
    bucket_simple = sum(1 for row in table_data if row['complexity_bucket'] == 'Simple')
    bucket_moderate = sum(1 for row in table_data if row['complexity_bucket'] == 'Moderate')
    bucket_complex = sum(1 for row in table_data if row['complexity_bucket'] == 'Complex')
    bucket_very_complex = sum(1 for row in table_data if row['complexity_bucket'] == 'Very complex')

    md_content.append("\n### Complexity Distribution\n")
    md_content.append(f"- **Simple (0.0-2.5):** {bucket_simple} APIs\n")
    md_content.append(f"- **Moderate (2.6-5.0):** {bucket_moderate} APIs\n")
    md_content.append(f"- **Complex (5.1-7.5):** {bucket_complex} APIs\n")
    md_content.append(f"- **Very complex (7.6-10.0):** {bucket_very_complex} APIs\n")

    md_content.append("\n## Complexity Scoring Legend\n")
    md_content.append("The **Complexity Score** (0-10 scale) is calculated from 10 structural signals:\n")
    md_content.append("- Authentication requirements, endpoint count, schema depth, response size\n")
    md_content.append("- Error surface, error codes count, pagination support & pattern\n")
    md_content.append("- Parameter complexity, rate limiting complexity\n")
    md_content.append("- Adjusted by documentation quality (high docs reduce score, low docs increase it)\n\n")
    md_content.append("**Buckets:**\n")
    md_content.append("- **Simple:** 0.0-2.5 — Minimal complexity, few parameters, simple responses\n")
    md_content.append("- **Moderate:** 2.6-5.0 — Standard REST APIs with moderate features\n")
    md_content.append("- **Complex:** 5.1-7.5 — Many endpoints, deep schemas, or complex patterns\n")
    md_content.append("- **Very complex:** 7.6-10.0 — Highly sophisticated APIs with many advanced features\n")

    md_content.append("\n## Complexity Signals Table\n")
    md_content.append("| API Name | Service | Auth | Pagination | Endpoints | Schema Depth | Avg Size (KB) | Error Surface | Complexity Score | Complexity Bucket |\n")
    md_content.append("|----------|---------|------|------------|-----------|--------------|---------------|---------------|------------------|-------------------|\n")

    for row in table_data:
        md_content.append(
            f"| {row['api_name']} | {row['service_name']} | {row['auth_required']} | "
            f"{row['pagination']} | {row['endpoints_count']} | {row['schema_depth']} | "
            f"{row['avg_response_kb']} | {row['error_surface']} | "
            f"{row['complexity_score']} | {row['complexity_bucket']} |\n"
        )

    md_content.append("\n## Detailed Notes\n")
    for row in table_data:
        if row['notes']:
            md_content.append(f"\n### {row['api_name']}\n")
            md_content.append(f"**Service:** {row['service_name']}\n\n")
            md_content.append(f"{row['notes']}\n")

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(md_content)

    print(f"✓ Report generated: {output_path}")


def main():
    """Main execution function."""
    print("API Audit Script - Phase 0.1")
    print("=" * 50)

    # Load configurations
    print("\n1. Loading API configurations...")
    apis = parse_apis_config("config/apis.txt")
    print(f"   ✓ Loaded {len(apis)} API test scenarios")

    print("\n2. Loading API metadata...")
    metadata = load_api_metadata("config/api_metadata.yaml")
    print(f"   ✓ Loaded metadata for {len(metadata)} API services")

    print("\n3. Generating complexity signals table...")
    table_data = generate_signals_table(apis, metadata)
    print(f"   ✓ Generated signals for {len(table_data)} APIs")

    # Check for missing metadata
    missing = [row for row in table_data if row['service_name'] == 'unknown']
    if missing:
        print(f"\n   ⚠ Warning: {len(missing)} APIs missing metadata:")
        for row in missing:
            print(f"      - {row['api_name']}")

    print("\n4. Generating markdown report...")
    generate_markdown_report(table_data, "docs/phase0_api_signals.md")

    print("\n" + "=" * 50)
    print("✓ Audit complete!")
    print(f"✓ Report saved to: docs/phase0_api_signals.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())

