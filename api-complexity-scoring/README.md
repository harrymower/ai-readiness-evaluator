# API Complexity Scoring

A standalone Python package for automatically analyzing APIs and scoring their complexity using both programmatic analysis and LLM-based assessments.

## Features

✅ **Programmatic Analysis** - Extract objective metrics without LLMs:
- Response size and schema depth
- Pagination pattern detection
- Rate limiting detection
- Authentication requirements

✅ **LLM Analysis** - Assess subjective complexity:
- Parameter complexity
- Error surface analysis
- Documentation quality

✅ **Comprehensive Analysis** - Combines programmatic and LLM insights for a holistic view.

## Installation

```bash
# Install in editable mode
cd api-complexity-scoring
pip install -e .
```

## Quick Start

### Analyze a Single Endpoint (Programmatic Only)

```bash
python src/api_analysis/cli.py analyze "curl https://api.github.com/users/octocat"
```

Output:
```
📊 Metrics:
   Status Code:        200
   Response Size:      1.32 KB
   Schema Depth:       shallow
   Pagination:         False (none)
   Rate Limiting:      complex
   Auth Required:      False
```

### Analyze a Single Endpoint (LLM Only)

```bash
python src/api_analysis/cli.py analyze --llm "curl https://api.github.com/users/octocat"
```

Output:
```
🧠 LLM Analysis:
   Parameter Complexity: low (no query/path params)
   Error Surface:        medium (standard HTTP errors, some custom)
   Documentation Quality: high (clear, examples provided)
```

### Analyze a Single Endpoint (Comprehensive)

```bash
python src/api_analysis/cli.py analyze --full-pipeline "curl https://api.github.com/users/octocat"
```

Output:
```
📊 Metrics:
   Status Code:        200
   Response Size:      1.32 KB
   Schema Depth:       shallow
   Pagination:         False (none)
   Rate Limiting:      complex
   Auth Required:      False

🧠 LLM Analysis:
   Parameter Complexity: low (no query/path params)
   Error Surface:        medium (standard HTTP errors, some custom)
   Documentation Quality: high (clear, examples provided)
```

### Analyze Multiple Endpoints

Create a file with curl commands (one per line):

```bash
# commands.txt
curl https://api.github.com/users/octocat
curl https://api.github.com/users/octocat/repos
curl https://api.github.com/repos/octocat/hello-world
```

Then analyze (add `--llm` or `--full-pipeline` for LLM analysis):

```bash
python src/api_analysis/cli.py analyze --file commands.txt --full-pipeline
```

### Python API

```python
from api_analysis.analyzers.programmatic import analyze_api_programmatically
from api_analysis.analyzers.llm import analyze_api_with_llm
from api_analysis.analyzers.comprehensive import analyze_api_comprehensively

# Analyze an endpoint programmatically
result_programmatic = analyze_api_programmatically('curl https://api.github.com/users')
print(f"Schema depth: {result_programmatic['schema_depth']}")

# Analyze an endpoint with LLM
result_llm = analyze_api_with_llm('curl https://api.github.com/users')
print(f"LLM Parameter Complexity: {result_llm['parameter_complexity']}")

# Analyze an endpoint comprehensively
result_comprehensive = analyze_api_comprehensively('curl https://api.github.com/users')
print(f"Comprehensive Schema depth: {result_comprehensive['programmatic']['schema_depth']}")
print(f"Comprehensive LLM Error Surface: {result_comprehensive['llm']['error_surface']}")
```

## Metrics Explained

### Schema Depth
- **shallow** (≤2 levels): Simple, flat responses
- **medium** (3-4 levels): Moderate nesting
- **deep** (≥5 levels): Complex, deeply nested structures

### Pagination Patterns
- **cursor**: Cursor-based pagination (e.g., GraphQL)
- **offset_limit**: Offset/limit pagination
- **page_size**: Page number pagination
- **none**: No pagination detected

### Rate Limiting
- **none**: No rate limiting detected
- **simple**: Basic rate limiting (1-2 headers)
- **complex**: Advanced rate limiting (3+ headers, multiple tiers)

### LLM Analysis Metrics
- **Parameter Complexity**: Assesses the complexity of request parameters (path, query, body).
  - **low**: Few or simple parameters.
  - **medium**: Moderate number or complexity of parameters.
  - **high**: Many, nested, or complex parameters (e.g., conditional logic).
- **Error Surface Analysis**: Evaluates the clarity and comprehensiveness of error responses.
  - **low**: Generic errors, unclear messages.
  - **medium**: Standard HTTP errors with some custom details.
  - **high**: Detailed, well-documented error codes and messages.
- **Documentation Quality**: Scores the clarity, completeness, and examples in the API documentation for the endpoint.
  - **low**: Missing or poor documentation.
  - **medium**: Basic documentation, some gaps.
  - **high**: Comprehensive, clear, and well-structured documentation with examples.
