# Design: API Metadata Analyzer - Standalone Service

## Executive Summary

This document outlines the design for a **standalone, reusable service** that automatically analyzes APIs and generates metadata assessments using LLMs. The service is designed to be:

- **Standalone**: Can be extracted into its own repository and run independently
- **Reusable**: Works with any API, not just this project's 26 APIs
- **Extensible**: Easy to add new metadata fields, LLM providers, or analysis strategies
- **Production-ready**: Suitable for use as a microservice or CLI tool in other projects

While initially developed for the AI Readiness Evaluator project to populate `config/api_metadata.yaml`, this service is architected as a general-purpose API analysis tool that can be used by any project needing automated API metadata generation.

## Problem Statement

**Current State:**
- `config/api_metadata.yaml` contains 26 APIs with 11 metadata fields each
- A human manually researches each API (reads docs, tests endpoints, makes assessments)
- Fields include objective data (e.g., `total_endpoints: 80`) and subjective assessments (e.g., `parameter_complexity: low`)
- Time-consuming, not scalable, prone to inconsistency

**Desired State:**
- Automated, programmatic analysis of APIs
- Reproducible and consistent assessments
- Scalable to hundreds of APIs
- Minimal human intervention (but reviewable if needed)

## Architecture Overview

### Approach: **Hybrid Multi-Stage Pipeline**

We'll use a pragmatic, three-stage approach that balances automation with accuracy:

```
Stage 1: Programmatic Analysis (No LLM)
  ↓
Stage 2: Documentation Analysis (LLM)
  ↓
Stage 3: Validation & Merging
  ↓
Output: YAML metadata
```

### Why This Approach?

1. **Hybrid = Best of Both Worlds**: Programmatic for objective metrics (fast, accurate), LLM for subjective assessments (intelligent, nuanced)
2. **Simple Architecture**: Single script, easy to understand and maintain
3. **Scalable**: Can process hundreds of APIs in batch
4. **Reproducible**: Same inputs → same outputs
5. **Cost-Effective**: Minimize LLM calls, use cheapest models where appropriate

## Detailed Design

### Stage 1: Programmatic Analysis

**Objective**: Extract measurable metrics without LLM

**Inputs:**
- API configuration from `config/apis.txt` (curl command, docs URL, base URL)

**Process:**
1. Execute the curl command
2. Measure response size (KB)
3. Parse JSON response to calculate schema depth
4. Check response headers for rate limiting indicators
5. Detect pagination from response structure (next/prev links, cursor fields)
6. Count error codes from sample requests

**Outputs:**
- `avg_response_size_kb` (measured)
- `schema_depth` (calculated: shallow ≤2 levels, medium 3-4, deep ≥5)
- `pagination_supported` (detected from response)
- `pagination_pattern` (detected: cursor, offset_limit, page_size, etc.)
- `rate_limiting` (detected from headers: X-RateLimit-*, Retry-After, etc.)

**Implementation:**
```python
def analyze_api_programmatically(curl_command: str) -> Dict[str, Any]:
    # Execute curl
    response = execute_curl(curl_command)
    
    # Measure response size
    size_kb = len(response.content) / 1024
    
    # Calculate schema depth
    depth = calculate_json_depth(response.json())
    
    # Detect pagination
    pagination_info = detect_pagination(response.json(), response.headers)
    
    # Detect rate limiting
    rate_limit_info = detect_rate_limiting(response.headers)
    
    return {
        'avg_response_size_kb': round(size_kb, 1),
        'schema_depth': classify_depth(depth),
        'pagination_supported': pagination_info['supported'],
        'pagination_pattern': pagination_info['pattern'],
        'rate_limiting': rate_limit_info['complexity']
    }
```

### Stage 2: Documentation Analysis (LLM)

**Objective**: Use LLM to assess subjective fields and fill gaps

**LLM Selection Research:**

Based on research of structured output capabilities and pricing:

| Model | Structured Output | Cost (per 1M tokens) | Best For |
|-------|------------------|---------------------|----------|
| **GPT-4o-mini** | ✅ JSON Schema (strict) | $0.15 input / $0.60 output | General analysis, cost-effective |
| **Claude 3.5 Sonnet** | ✅ Tool Use (schema) | $3.00 input / $15.00 output | Complex reasoning, high quality |
| **Gemini 2.0 Flash** | ✅ Response Schema | $0.075 input / $0.30 output | **BEST: Cheapest + reliable** |

**Recommendation: Gemini 2.0 Flash**
- **50% cheaper** than GPT-4o-mini
- Native structured output support (`response_schema`)
- Fast and reliable for documentation analysis
- Good at parsing technical documentation

**Fallback: GPT-4o-mini** for complex cases or if Gemini fails

**Inputs:**
- Documentation URL (fetched HTML/markdown)
- API base URL
- Programmatic analysis results (for context)

**Process:**
1. Fetch documentation page
2. Extract text content (strip HTML, keep structure)
3. Single LLM call with structured prompt
4. Request JSON output with all subjective fields + reasoning

**Prompt Template:**
```
You are an API complexity analyst. Analyze the following API documentation and provide assessments.

API: {api_name}
Base URL: {base_url}
Documentation: {doc_content}

Programmatic Analysis Results:
- Response size: {size_kb} KB
- Schema depth: {depth}
- Pagination detected: {pagination}

Assess the following fields:

1. total_endpoints: Count or estimate the number of API endpoints
2. auth_required: yes/no/optional - Does the API require authentication?
3. parameter_complexity: low/medium/high - Typical request parameter complexity
4. error_surface: low/medium/high - Variety of error codes/scenarios
5. error_codes_count: Approximate number of distinct HTTP error codes (4xx/5xx)
6. doc_coverage: low/medium/high - Documentation quality and completeness

Return JSON with this exact structure:
{
  "total_endpoints": <integer>,
  "auth_required": "<yes|no|optional>",
  "parameter_complexity": "<low|medium|high>",
  "error_surface": "<low|medium|high>",
  "error_codes_count": <integer>,
  "doc_coverage": "<low|medium|high>",
  "reasoning": {
    "total_endpoints": "<brief explanation>",
    "auth_required": "<brief explanation>",
    ...
  },
  "confidence": {
    "total_endpoints": <0.0-1.0>,
    "auth_required": <0.0-1.0>,
    ...
  }
}
```

**Implementation:**
```python
def analyze_api_with_llm(doc_url: str, api_name: str, programmatic_results: Dict) -> Dict[str, Any]:
    # Fetch documentation
    doc_content = fetch_and_clean_documentation(doc_url)

    # Build prompt
    prompt = build_analysis_prompt(api_name, doc_content, programmatic_results)

    # Call Gemini 2.0 Flash with structured output
    response = call_gemini_with_schema(prompt, METADATA_SCHEMA)

    return response
```

### Stage 3: Validation & Merging

**Objective**: Combine results, validate, and generate final YAML

**Process:**
1. Merge programmatic + LLM results
2. Cross-validate for consistency
3. Apply business rules
4. Flag low-confidence assessments
5. Generate YAML output

**Validation Rules:**
- If LLM says `auth_required: no` but programmatic analysis detected auth headers → flag for review
- If `total_endpoints` from LLM differs significantly from discovered endpoints → use LLM value but flag
- If confidence score < 0.7 for any field → mark as `unknown` or flag for human review
- Ensure all enum values are valid (low/medium/high, yes/no/optional, etc.)

**Implementation:**
```python
def merge_and_validate(programmatic: Dict, llm: Dict, api_name: str) -> Dict[str, Any]:
    merged = {}
    flags = []

    # Merge results (LLM takes precedence for subjective fields)
    merged.update(programmatic)  # Objective metrics
    merged.update(llm)  # Subjective assessments

    # Cross-validation
    if llm.get('auth_required') == 'no' and programmatic.get('auth_detected'):
        flags.append('auth_mismatch')

    # Confidence filtering
    for field, confidence in llm.get('confidence', {}).items():
        if confidence < 0.7:
            merged[field] = 'unknown'
            flags.append(f'low_confidence_{field}')

    # Validate enums
    validate_enum_values(merged)

    return {
        'metadata': merged,
        'flags': flags,
        'confidence_scores': llm.get('confidence', {}),
        'reasoning': llm.get('reasoning', {})
    }
```

## Implementation Plan

### Standalone Service Architecture

The service will be designed as a **standalone Python package** that can be:
1. Used as a **CLI tool** (`api-metadata-analyzer`)
2. Imported as a **Python library** (`from api_metadata_analyzer import analyze_api`)
3. Deployed as a **microservice** (REST API)
4. Integrated into CI/CD pipelines

### Repository Structure (Standalone)

```
api-metadata-analyzer/                    # Standalone repository
├── README.md                             # Project overview, quick start
├── LICENSE                               # MIT or Apache 2.0
├── setup.py / pyproject.toml             # Package configuration
├── requirements.txt                      # Dependencies
├── .env.example                          # Example environment variables
├── .gitignore
│
├── api_metadata_analyzer/                # Main package
│   ├── __init__.py                       # Package exports
│   ├── cli.py                            # CLI entry points
│   ├── config.py                         # Configuration management
│   ├── models.py                         # Pydantic models
│   │
│   ├── analyzers/                        # Analysis modules
│   │   ├── __init__.py
│   │   ├── programmatic.py               # Stage 1: Programmatic analysis
│   │   ├── llm_analyzer.py               # Stage 2: LLM analysis
│   │   ├── openapi_parser.py             # OpenAPI spec parsing
│   │   └── documentation_fetcher.py      # Fetch and clean docs
│   │
│   ├── validators/                       # Validation modules
│   │   ├── __init__.py
│   │   ├── validators.py                 # Cross-validation logic
│   │   └── confidence_filter.py          # Confidence-based filtering
│   │
│   ├── outputs/                          # Output generators
│   │   ├── __init__.py
│   │   ├── yaml_generator.py             # YAML output
│   │   ├── json_generator.py             # JSON output
│   │   └── markdown_generator.py         # Markdown reports
│   │
│   └── llm_providers/                    # LLM integrations
│       ├── __init__.py
│       ├── base.py                       # Abstract base class
│       ├── gemini.py                     # Gemini 2.0 Flash
│       ├── openai.py                     # GPT-4o-mini
│       └── anthropic.py                  # Claude 3.5 Sonnet
│
├── tests/                                # Test suite
│   ├── __init__.py
│   ├── conftest.py                       # Pytest fixtures
│   ├── test_analyzers/
│   │   ├── test_programmatic.py
│   │   ├── test_llm_analyzer.py
│   │   └── test_openapi_parser.py
│   ├── test_validators/
│   │   └── test_validators.py
│   ├── test_llm_providers/
│   │   ├── test_gemini.py
│   │   ├── test_openai.py
│   │   └── test_anthropic.py
│   └── integration/
│       └── test_full_pipeline.py
│
├── examples/                             # Example usage
│   ├── basic_usage.py
│   ├── batch_processing.py
│   ├── custom_schema.py
│   └── sample_outputs/
│       ├── example_api.yaml
│       ├── example_api.json
│       └── batch_report.md
│
├── docs/                                 # Documentation
│   ├── user_guide.md
│   ├── developer_guide.md
│   ├── api_reference.md
│   ├── architecture.md
│   └── extending.md
│
└── scripts/                              # Utility scripts
    ├── analyze_single.py                 # Single API analysis
    ├── analyze_batch.py                  # Batch processing
    └── validate_results.py               # Validation tool
```

### Integration with AI Readiness Evaluator

The AI Readiness Evaluator project will use this as a **dependency**:

```
ai-readiness-evaluator/
├── requirements.txt                      # Add: api-metadata-analyzer>=1.0.0
├── config/
│   ├── apis.txt                          # API configurations (input)
│   └── api_metadata.yaml                 # Generated metadata (output)
└── scripts/
    └── generate_api_metadata.py          # Wrapper script that calls analyzer
```

### CLI Usage (Standalone Package)

Once installed as a package (`pip install api-metadata-analyzer`), users can use the CLI:

```bash
# Analyze single API from URL
api-metadata-analyzer analyze \
  --url "https://api.example.com/v1/users" \
  --docs-url "https://api.example.com/docs" \
  --output result.yaml

# Analyze with specific LLM
api-metadata-analyzer analyze \
  --url "https://swapi.dev/api/people/1" \
  --docs-url "https://swapi.dev/documentation" \
  --llm gemini-2.0-flash \
  --format json

# Batch analyze from config file
api-metadata-analyzer batch \
  --config apis.yaml \
  --output-dir results/ \
  --parallel --workers 10

# Validate generated metadata
api-metadata-analyzer validate \
  --generated results/metadata.yaml \
  --reference baseline/metadata.yaml \
  --report validation_report.md
```

### Python Library Usage

```python
from api_metadata_analyzer import APIAnalyzer, AnalyzerConfig

# Initialize analyzer
config = AnalyzerConfig(
    llm_provider="gemini-2.0-flash",
    confidence_threshold=0.7,
    use_openapi=True
)
analyzer = APIAnalyzer(config)

# Analyze single API
result = analyzer.analyze(
    url="https://api.example.com/v1/users",
    docs_url="https://api.example.com/docs"
)

print(f"Complexity Score: {result.metadata.complexity_score}")
print(f"Confidence: {result.average_confidence}")
print(f"Flags: {result.flags}")

# Export to YAML
result.to_yaml("output.yaml")

# Batch processing
from api_metadata_analyzer import BatchAnalyzer

batch = BatchAnalyzer(config)
results = batch.analyze_from_config("apis.yaml", parallel=True, workers=5)

# Generate summary report
batch.generate_report(results, "summary.md")
```

### Input Configuration Format

The service accepts API configurations in a **flexible, standardized format**:

```yaml
# apis.yaml - Input configuration
apis:
  - name: "example_api"
    base_url: "https://api.example.com"
    sample_endpoint: "https://api.example.com/v1/users"
    documentation_url: "https://api.example.com/docs"
    openapi_spec_url: "https://api.example.com/openapi.json"  # optional

  - name: "another_api"
    base_url: "https://api.another.com"
    sample_endpoint: "https://api.another.com/v1/data"
    documentation_url: "https://api.another.com/documentation"
```

This format is **independent** of the AI Readiness Evaluator's `apis.txt` format, making the service truly reusable.

## Error Handling & Edge Cases

### Documentation Not Available
- **Fallback**: Use LLM with just the curl command and response
- **Strategy**: Ask LLM to infer from API response structure
- **Mark**: Set `doc_coverage: unknown` and flag for review

### API Requires Authentication
- **Detection**: Check if curl command fails with 401/403
- **Fallback**: Analyze error response and any public docs
- **Mark**: Set `auth_required: yes` and use LLM for other fields

### Rate Limiting During Analysis
- **Detection**: 429 status code or rate limit headers
- **Strategy**: Exponential backoff, retry with delays
- **Fallback**: Skip programmatic analysis, rely on LLM + docs

### LLM Returns Invalid Data
- **Validation**: Strict schema validation with Pydantic
- **Retry**: Retry with clarified prompt (up to 3 times)
- **Fallback**: Use GPT-4o-mini if Gemini fails
- **Last Resort**: Mark fields as `unknown`

### Documentation is Interactive (Swagger UI)
- **Detection**: Check for Swagger/OpenAPI UI patterns
- **Strategy**: Try to extract OpenAPI JSON from page
- **Fallback**: Fetch raw HTML and let LLM parse it
- **Best Effort**: LLMs are good at parsing Swagger UI HTML

### API Has Hundreds of Endpoints
- **Strategy**: LLM estimates from documentation structure
- **Validation**: Cross-check with OpenAPI spec if available
- **Confidence**: Lower confidence score if estimated

## Cost Analysis

### Per-API Cost Estimate

**Assumptions:**
- Average documentation page: ~10,000 tokens
- LLM response: ~500 tokens
- Using Gemini 2.0 Flash

**Cost per API:**
- Input: 10,000 tokens × $0.075 / 1M = $0.00075
- Output: 500 tokens × $0.30 / 1M = $0.00015
- **Total: ~$0.001 per API**

**For 100 APIs:** ~$0.10
**For 1000 APIs:** ~$1.00

**Extremely cost-effective!**

### Comparison with Manual Process

| Method | Time per API | Cost per API | Quality | Scalability |
|--------|-------------|--------------|---------|-------------|
| **Manual** | 30-60 min | $25-50 (labor) | High (but inconsistent) | Poor |
| **Automated** | 10-30 sec | $0.001 | High (consistent) | Excellent |

**ROI:** Even for 26 APIs, saves ~20 hours of human time

## Validation Strategy

### Automated Validation
1. **Schema Validation**: Pydantic models for all fields
2. **Enum Validation**: Ensure values match allowed options
3. **Cross-Field Validation**: Check for logical inconsistencies
4. **Confidence Thresholds**: Flag low-confidence assessments

### Human Review (Optional)
1. **Review Mode**: Generate report of flagged APIs
2. **Diff View**: Show changes vs. existing metadata
3. **Confidence Dashboard**: Sort by confidence scores
4. **Spot Checking**: Manually verify 10% of results

### Quality Metrics
- **Accuracy**: Compare against existing manual assessments (for 26 APIs)
- **Consistency**: Run same API multiple times, check variance
- **Completeness**: % of fields successfully populated
- **Confidence**: Average confidence scores across all fields

## OpenAPI Spec Handling

### Discovery Strategy
1. **Check common locations**:
   - `/openapi.json`
   - `/swagger.json`
   - `/api-docs`
   - `/v1/openapi.json`
2. **Parse documentation** for OpenAPI links
3. **Ask LLM** if it sees OpenAPI spec references

### If OpenAPI Spec Found
- **Priority**: Use spec as primary source of truth
- **Extract**: `total_endpoints`, `auth_required`, `parameter_complexity`
- **Validate**: Cross-check with programmatic analysis
- **Confidence**: High (0.95+) for spec-derived fields

### If No OpenAPI Spec
- **Fallback**: Documentation + programmatic analysis
- **Confidence**: Medium (0.7-0.85) for estimated fields

## Standalone Service Deployment Options

### 1. CLI Tool (Primary)
- Install via pip: `pip install api-metadata-analyzer`
- Use from command line: `api-metadata-analyzer analyze --url ...`
- Integrate into shell scripts and CI/CD pipelines

### 2. Python Library
- Import in Python projects: `from api_metadata_analyzer import APIAnalyzer`
- Programmatic access to all functionality
- Customize analysis pipeline

### 3. REST API Microservice (Future)
```python
# FastAPI-based microservice
from fastapi import FastAPI
from api_metadata_analyzer import APIAnalyzer

app = FastAPI()

@app.post("/analyze")
async def analyze_api(request: AnalyzeRequest):
    analyzer = APIAnalyzer(config)
    result = analyzer.analyze(
        url=request.url,
        docs_url=request.docs_url
    )
    return result.to_dict()

@app.post("/batch")
async def batch_analyze(request: BatchRequest):
    batch = BatchAnalyzer(config)
    results = batch.analyze_from_config(request.config)
    return {"results": [r.to_dict() for r in results]}
```

### 4. Docker Container (Future)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install api-metadata-analyzer
ENTRYPOINT ["api-metadata-analyzer"]
```

```bash
# Run as container
docker run api-metadata-analyzer analyze --url https://api.example.com
```

## Extensibility & Customization

### Custom Metadata Schema

Users can define their own metadata fields:

```python
from api_metadata_analyzer import APIAnalyzer, MetadataSchema
from pydantic import BaseModel

class CustomMetadata(MetadataSchema):
    # Inherit base fields
    # Add custom fields
    api_version: str
    supports_graphql: bool
    data_format: str  # json, xml, protobuf

analyzer = APIAnalyzer(schema=CustomMetadata)
result = analyzer.analyze(url="...", docs_url="...")
```

### Custom LLM Provider

Users can add their own LLM providers:

```python
from api_metadata_analyzer.llm_providers import BaseLLMProvider

class CustomLLMProvider(BaseLLMProvider):
    def analyze(self, prompt: str, schema: dict) -> dict:
        # Custom implementation
        pass

analyzer = APIAnalyzer(llm_provider=CustomLLMProvider())
```

### Custom Validation Rules

Users can add custom validation logic:

```python
from api_metadata_analyzer.validators import BaseValidator

class CustomValidator(BaseValidator):
    def validate(self, programmatic: dict, llm: dict) -> list[str]:
        flags = []
        # Custom validation logic
        return flags

analyzer = APIAnalyzer(validators=[CustomValidator()])
```

## Future Enhancements

### Phase 2 (Optional)
1. **Multi-LLM Consensus**: Use 2-3 LLMs, take majority vote
2. **Active Learning**: Learn from human corrections
3. **Incremental Updates**: Re-analyze only changed APIs
4. **API Change Detection**: Monitor for API updates
5. **Confidence Calibration**: Tune confidence thresholds based on accuracy
6. **REST API Microservice**: Deploy as HTTP service
7. **Docker Support**: Containerized deployment

### Phase 3 (Optional)
1. **Real-Time Analysis**: Analyze new APIs on-demand
2. **API Comparison**: Compare similar APIs
3. **Trend Analysis**: Track API complexity over time
4. **Recommendation Engine**: Suggest similar APIs
5. **Web UI**: Browser-based interface for analysis
6. **Plugin System**: Community-contributed analyzers and validators
7. **Cloud Deployment**: AWS Lambda, Google Cloud Functions, Azure Functions

## Success Criteria

### Must Have
- ✅ Analyze all 26 existing APIs successfully
- ✅ Generate valid YAML matching current schema
- ✅ 90%+ accuracy vs. manual assessments
- ✅ < 1 minute per API processing time
- ✅ < $0.01 per API cost

### Should Have
- ✅ Confidence scores for all assessments
- ✅ Reasoning/explanation for each field
- ✅ Validation and error handling
- ✅ Batch processing support
- ✅ Human review workflow

### Nice to Have
- ⭕ OpenAPI spec auto-discovery
- ⭕ Multi-LLM support (Gemini, GPT, Claude)
- ⭕ Parallel processing
- ⭕ Diff generation vs. existing metadata

## Next Steps

See GitHub issues for detailed implementation tasks.

