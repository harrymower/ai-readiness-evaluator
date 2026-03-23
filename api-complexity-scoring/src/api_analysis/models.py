"""
Pydantic models for API metadata and analysis results.

This module defines the data models used throughout the API Metadata Analyzer:
- APIMetadata: The 11 metadata fields for an API
- AnalysisResult: Complete analysis result with metadata, confidence, and reasoning
- LLMAnalysisResult: LLM-specific analysis result
- AnalyzerConfig: Configuration for the analyzer
"""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class APIMetadata(BaseModel):
    """
    API metadata model with 11 fields.
    
    This model represents the complete metadata assessment for an API,
    including both objective (programmatically determined) and subjective
    (LLM-assessed) fields.
    """
    
    # Basic information
    service_name: str = Field(
        description="Human-readable name of the API service"
    )
    
    # Objective fields (programmatically determined)
    total_endpoints: int = Field(
        ge=0,
        description="Total number of API endpoints"
    )
    
    error_codes_count: int = Field(
        ge=0,
        description="Number of distinct error codes documented"
    )
    
    avg_response_size_kb: float = Field(
        ge=0.0,
        description="Average response size in kilobytes"
    )
    
    auth_required: Literal['yes', 'no', 'optional', 'unknown'] = Field(
        description="Whether authentication is required"
    )
    
    # Semi-objective fields (detectable from responses)
    pagination_supported: bool = Field(
        description="Whether the API supports pagination"
    )
    
    pagination_pattern: Literal[
        'none', 'offset_limit', 'page_size', 'cursor', 'mixed', 'other', 'unknown'
    ] = Field(
        description="Type of pagination pattern used"
    )
    
    rate_limiting: Literal['none', 'simple', 'complex', 'unknown'] = Field(
        description="Complexity of rate limiting implementation"
    )
    
    schema_depth: Literal['shallow', 'medium', 'deep', 'unknown'] = Field(
        description="Depth and complexity of response schema"
    )
    
    # Subjective fields (LLM-assessed)
    parameter_complexity: Literal['low', 'medium', 'high', 'unknown'] = Field(
        description="Complexity of request parameters"
    )
    
    doc_coverage: Literal['low', 'medium', 'high', 'unknown'] = Field(
        description="Quality and completeness of documentation"
    )
    
    error_surface: Literal['low', 'medium', 'high', 'unknown'] = Field(
        description="Variety and complexity of error handling"
    )
    
    @field_validator('pagination_pattern')
    @classmethod
    def validate_pagination_pattern(cls, v: str, info) -> str:
        """Ensure pagination_pattern is 'none' if pagination_supported is False."""
        # Note: info.data contains other fields that have been validated so far
        if 'pagination_supported' in info.data:
            if not info.data['pagination_supported'] and v != 'none':
                return 'none'
        return v
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "service_name": "Example API",
                "total_endpoints": 50,
                "auth_required": "yes",
                "pagination_supported": True,
                "schema_depth": "medium",
                "avg_response_size_kb": 15.5,
                "error_surface": "medium",
                "parameter_complexity": "medium",
                "pagination_pattern": "offset_limit",
                "rate_limiting": "simple",
                "doc_coverage": "high",
                "error_codes_count": 8
            }
        }


class AnalysisResult(BaseModel):
    """
    Complete analysis result for an API.
    
    Contains the metadata assessment, confidence scores for each field,
    reasoning for subjective assessments, and any flags for human review.
    """
    
    metadata: APIMetadata = Field(
        description="The assessed API metadata"
    )
    
    confidence_scores: Dict[str, float] = Field(
        description="Confidence score (0.0-1.0) for each metadata field"
    )
    
    reasoning: Dict[str, str] = Field(
        description="Explanation for each subjective assessment"
    )
    
    flags: List[str] = Field(
        default_factory=list,
        description="Flags for human review (e.g., low confidence, conflicts)"
    )
    
    source: Literal['programmatic', 'llm', 'merged'] = Field(
        default='merged',
        description="Source of the analysis result"
    )
    
    llm_provider: Optional[str] = Field(
        default=None,
        description="LLM provider used (if applicable)"
    )
    
    @property
    def average_confidence(self) -> float:
        """Calculate average confidence across all fields."""
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores.values()) / len(self.confidence_scores)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()
    
    def to_yaml(self, filepath: str) -> None:
        """Export to YAML file (implementation in outputs module)."""
        raise NotImplementedError("Use outputs.yaml_generator module")
    
    def to_json(self, filepath: str) -> None:
        """Export to JSON file (implementation in outputs module)."""
        raise NotImplementedError("Use outputs.json_generator module")


class LLMAnalysisResult(BaseModel):
    """
    Result from LLM analysis of API documentation.
    
    Contains subjective assessments that require LLM understanding,
    along with reasoning and confidence scores for each field.
    """
    
    total_endpoints: int = Field(
        ge=0,
        description="Total number of API endpoints identified from documentation"
    )
    
    auth_required: Literal['yes', 'no', 'optional', 'unknown'] = Field(
        description="Whether authentication is required"
    )
    
    parameter_complexity: Literal['low', 'medium', 'high', 'unknown'] = Field(
        description="Complexity of request parameters across endpoints"
    )
    
    error_surface: Literal['low', 'medium', 'high', 'unknown'] = Field(
        description="Variety and complexity of error handling"
    )
    
    error_codes_count: int = Field(
        ge=0,
        description="Number of distinct error codes documented"
    )
    
    doc_coverage: Literal['low', 'medium', 'high', 'unknown'] = Field(
        description="Quality and completeness of documentation"
    )
    
    reasoning: Dict[str, str] = Field(
        description="Explanation for each field assessment"
    )
    
    confidence: Dict[str, float] = Field(
        description="Confidence score (0.0-1.0) for each field"
    )
    
    @property
    def average_confidence(self) -> float:
        """Calculate average confidence across all fields."""
        if not self.confidence:
            return 0.0
        return sum(self.confidence.values()) / len(self.confidence)


class AnalyzerConfig(BaseModel):
    """Configuration for the API Metadata Analyzer."""
    
    llm_provider: Literal['gemini-2.0-flash', 'gpt-4o-mini', 'claude-3.5-sonnet'] = Field(
        default='gemini-2.0-flash',
        description="LLM provider to use for analysis"
    )
    
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to accept (0.0-1.0)"
    )
    
    use_openapi: bool = Field(
        default=True,
        description="Whether to attempt OpenAPI spec discovery"
    )
    
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Timeout for HTTP requests in seconds"
    )
    
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retries for failed requests"
    )
    
    verbose: bool = Field(
        default=False,
        description="Enable verbose logging"
    )

