"""
Result validation and merging module.

Merges programmatic and LLM analysis results, validates consistency,
applies confidence filtering, and produces final AnalysisResult.
"""

from typing import Dict, List, Tuple

from ..models import APIMetadata, AnalysisResult, LLMAnalysisResult


def merge_results(
    programmatic: Dict,
    llm: LLMAnalysisResult
) -> Dict:
    """
    Merge programmatic and LLM analysis results.
    
    Strategy:
    - Prefer programmatic values for objective fields
    - Use LLM values for subjective fields
    - Handle conflicts intelligently
    
    Args:
        programmatic: Programmatic analysis results
        llm: LLM analysis results
        
    Returns:
        Merged metadata dict
    """
    merged = {}
    
    # Objective fields - prefer programmatic
    merged['avg_response_size_kb'] = programmatic.get('avg_response_size_kb', 0.0)
    merged['schema_depth'] = programmatic.get('schema_depth', 'unknown')
    merged['pagination_supported'] = programmatic.get('pagination_supported', False)
    merged['pagination_pattern'] = programmatic.get('pagination_pattern', 'none')
    merged['rate_limiting'] = programmatic.get('rate_limiting', 'none')
    
    # Auth - use programmatic if detected, otherwise LLM
    if programmatic.get('auth_detected', False):
        merged['auth_required'] = 'yes'
    else:
        merged['auth_required'] = llm.auth_required
    
    # Subjective fields - from LLM
    merged['total_endpoints'] = llm.total_endpoints
    merged['parameter_complexity'] = llm.parameter_complexity
    merged['error_surface'] = llm.error_surface
    merged['error_codes_count'] = llm.error_codes_count
    merged['doc_coverage'] = llm.doc_coverage
    
    return merged


def cross_validate(
    merged: Dict,
    programmatic: Dict,
    llm: LLMAnalysisResult
) -> List[str]:
    """
    Cross-validate merged results for inconsistencies.
    
    Args:
        merged: Merged metadata
        programmatic: Programmatic results
        llm: LLM results
        
    Returns:
        List of validation flags
    """
    flags = []
    
    # Check auth consistency
    prog_auth = programmatic.get('auth_detected', False)
    llm_auth = llm.auth_required in ['yes', 'optional']
    
    if prog_auth and llm.auth_required == 'no':
        flags.append(
            "CONFLICT: Programmatic analysis detected auth, but LLM says no auth required"
        )
    elif not prog_auth and llm.auth_required == 'yes':
        flags.append(
            "WARNING: LLM says auth required, but programmatic didn't detect it "
            "(may be in headers not visible in programmatic analysis)"
        )
    
    # Check pagination consistency
    prog_pagination = programmatic.get('pagination_supported', False)
    merged_pagination = merged.get('pagination_supported', False)
    
    if prog_pagination != merged_pagination:
        flags.append(
            f"INFO: Pagination detection discrepancy "
            f"(programmatic: {prog_pagination}, merged: {merged_pagination})"
        )
    
    return flags


def apply_confidence_filtering(
    merged: Dict,
    confidence: Dict[str, float],
    threshold: float = 0.7
) -> Tuple[Dict, List[str]]:
    """
    Apply confidence filtering to merged results.
    
    Sets low-confidence fields to 'unknown' and adds flags.
    
    Args:
        merged: Merged metadata
        confidence: Confidence scores for each field
        threshold: Minimum confidence threshold (0.7 default)
        
    Returns:
        Tuple of (filtered metadata, flags)
    """
    filtered = merged.copy()
    flags = []
    
    # Map LLM field names to metadata field names
    field_mapping = {
        'total_endpoints': 'total_endpoints',
        'auth_required': 'auth_required',
        'parameter_complexity': 'parameter_complexity',
        'error_surface': 'error_surface',
        'error_codes_count': 'error_codes_count',
        'doc_coverage': 'doc_coverage'
    }
    
    # Apply filtering
    for llm_field, metadata_field in field_mapping.items():
        conf = confidence.get(llm_field, 0.0)
        
        if conf < threshold:
            # Set to unknown for enums, 0 for integers
            if metadata_field in ['total_endpoints', 'error_codes_count']:
                # Don't change integer fields, but flag them
                flags.append(
                    f"LOW_CONFIDENCE: {metadata_field} has confidence {conf:.2f} "
                    f"(below {threshold})"
                )
            else:
                # Set enum fields to 'unknown'
                filtered[metadata_field] = 'unknown'
                flags.append(
                    f"LOW_CONFIDENCE: {metadata_field} set to 'unknown' "
                    f"(confidence: {conf:.2f}, threshold: {threshold})"
                )
    
    return filtered, flags


def validate_enums(metadata: Dict) -> List[str]:
    """
    Validate that enum fields have valid values.
    
    Args:
        metadata: Metadata dict
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Define valid enum values
    enum_fields = {
        'auth_required': ['yes', 'no', 'optional', 'unknown'],
        'pagination_pattern': ['none', 'offset_limit', 'page_size', 'cursor', 
                              'mixed', 'other', 'unknown'],
        'rate_limiting': ['none', 'simple', 'complex', 'unknown'],
        'schema_depth': ['shallow', 'medium', 'deep', 'unknown'],
        'parameter_complexity': ['low', 'medium', 'high', 'unknown'],
        'doc_coverage': ['low', 'medium', 'high', 'unknown'],
        'error_surface': ['low', 'medium', 'high', 'unknown']
    }
    
    # Validate each enum field
    for field, valid_values in enum_fields.items():
        if field in metadata:
            value = metadata[field]
            if value not in valid_values:
                errors.append(
                    f"INVALID_ENUM: {field}='{value}' not in {valid_values}"
                )
    
    return errors


def validate_and_merge(
    api_name: str,
    programmatic: Dict,
    llm: LLMAnalysisResult,
    confidence_threshold: float = 0.7
) -> AnalysisResult:
    """
    Main validation and merging orchestration function.
    
    Merges programmatic and LLM results, validates consistency,
    applies confidence filtering, and returns complete AnalysisResult.
    
    Args:
        api_name: API service name
        programmatic: Programmatic analysis results
        llm: LLM analysis results
        confidence_threshold: Confidence threshold for filtering
        
    Returns:
        Complete AnalysisResult with metadata, confidence, reasoning, and flags
    """
    # Step 1: Merge results
    merged = merge_results(programmatic, llm)
    
    # Add service name
    merged['service_name'] = api_name
    
    # Step 2: Cross-validate
    validation_flags = cross_validate(merged, programmatic, llm)
    
    # Step 3: Apply confidence filtering
    filtered, confidence_flags = apply_confidence_filtering(
        merged,
        llm.confidence,
        confidence_threshold
    )
    
    # Step 4: Validate enums
    enum_errors = validate_enums(filtered)
    
    # Combine all flags
    all_flags = validation_flags + confidence_flags + enum_errors
    
    # Create APIMetadata instance
    try:
        metadata = APIMetadata(**filtered)
    except Exception as e:
        # If validation fails, add error flag
        all_flags.append(f"METADATA_VALIDATION_ERROR: {str(e)}")
        # Try with defaults for missing fields
        for field in ['service_name', 'total_endpoints', 'auth_required',
                     'pagination_supported', 'schema_depth', 'avg_response_size_kb',
                     'error_surface', 'parameter_complexity', 'pagination_pattern',
                     'rate_limiting', 'doc_coverage', 'error_codes_count']:
            if field not in filtered:
                if field == 'service_name':
                    filtered[field] = api_name
                elif field in ['total_endpoints', 'error_codes_count']:
                    filtered[field] = 0
                elif field == 'avg_response_size_kb':
                    filtered[field] = 0.0
                elif field == 'pagination_supported':
                    filtered[field] = False
                else:
                    filtered[field] = 'unknown'
        metadata = APIMetadata(**filtered)
    
    # Create AnalysisResult
    return AnalysisResult(
        metadata=metadata,
        confidence_scores=llm.confidence,
        reasoning=llm.reasoning,
        flags=all_flags,
        source='merged',
        llm_provider=None  # Will be set by caller
    )
