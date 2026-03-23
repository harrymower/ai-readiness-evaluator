"""
YAML generation for API metadata output.

Generates YAML-formatted API metadata matching the project's api_metadata.yaml format.
"""

from datetime import datetime
from typing import List

import yaml

from ..models import APIMetadata, AnalysisResult


def generate_yaml_entry(api_name: str, metadata: APIMetadata) -> str:
    """
    Generate YAML entry for a single API.
    
    Args:
        api_name: API service name
        metadata: APIMetadata instance
        
    Returns:
        YAML string for single API entry
    """
    # Convert to dict
    data = metadata.model_dump()
    
    # Remove service_name from data (used as key)
    data.pop('service_name', None)
    
    # Format as YAML
    entry = {api_name: data}
    yaml_str = yaml.dump(entry, default_flow_style=False, sort_keys=False)
    
    return yaml_str


def generate_yaml_file(
    results: List[AnalysisResult],
    output_path: str,
    include_header: bool = True
) -> None:
    """
    Generate complete YAML file from multiple API results.
    
    Args:
        results: List of AnalysisResult instances
        output_path: Path to output YAML file
        include_header: Whether to include timestamp header
    """
    # Build complete data structure
    all_apis = {}
    
    for result in results:
        api_name = result.metadata.service_name
        metadata_dict = result.metadata.model_dump()
        metadata_dict.pop('service_name', None)  # Remove duplicate
        all_apis[api_name] = metadata_dict
    
    # Sort by API name
    sorted_apis = dict(sorted(all_apis.items()))
    
    # Generate YAML
    yaml_content = yaml.dump(sorted_apis, default_flow_style=False, sort_keys=False)
    
    # Add header if requested
    if include_header:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        header = f"""# API Metadata
# Generated: {timestamp}
# Total APIs: {len(sorted_apis)}

"""
        yaml_content = header + yaml_content
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
