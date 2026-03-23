# API Metadata Analyzer - Standalone Service Plan

## Vision

Create a **standalone, open-source Python package** that automatically analyzes APIs and generates metadata assessments using LLMs. This service will be:

- **Reusable**: Works with any API, not tied to this project
- **Extensible**: Easy to customize metadata schema, add LLM providers, extend validation
- **Production-ready**: CLI tool, Python library, and future microservice deployment
- **Community-driven**: Open for contributions, plugins, and extensions

## Repository Strategy

### Phase 1: Develop In-Tree (Current Project)
**Location**: `ai-readiness-evaluator/scripts/api_analysis/`

**Rationale**:
- Faster iteration during initial development
- Easy testing with real use case (26 APIs)
- Validate design decisions with actual data
- Build confidence in accuracy and reliability

**Timeline**: Issues #53-60 (1-2 weeks)

### Phase 2: Extract to Standalone Repository
**Location**: New repo `api-metadata-analyzer`

**When**: After Issue #60 is complete and validated

**Extraction Steps**:
1. Create new repository: `api-metadata-analyzer`
2. Move `scripts/api_analysis/` → `api_metadata_analyzer/` (package)
3. Add package configuration (`setup.py`, `pyproject.toml`)
4. Refactor to remove project-specific dependencies
5. Create standalone CLI entry points
6. Publish to PyPI as `api-metadata-analyzer`
7. Update `ai-readiness-evaluator` to use as dependency

### Phase 3: Community & Growth
**Location**: Standalone repo with community contributions

**Features**:
- Accept community contributions
- Plugin system for custom analyzers
- Support for more LLM providers
- REST API microservice
- Web UI
- Cloud deployment options

## Package Design

### Package Name
`api-metadata-analyzer`

### Installation
```bash
pip install api-metadata-analyzer
```

### CLI Commands
```bash
# Analyze single API
api-metadata-analyzer analyze --url <url> --docs-url <docs>

# Batch analyze
api-metadata-analyzer batch --config apis.yaml

# Validate results
api-metadata-analyzer validate --generated <file> --reference <file>
```

### Python API
```python
from api_metadata_analyzer import APIAnalyzer

analyzer = APIAnalyzer(llm_provider="gemini-2.0-flash")
result = analyzer.analyze(url="...", docs_url="...")
```

## Integration with AI Readiness Evaluator

### Before Extraction (Current)
```
ai-readiness-evaluator/
├── scripts/
│   └── api_analysis/          # Developed here
│       ├── programmatic.py
│       ├── llm_analyzer.py
│       └── ...
└── config/
    └── api_metadata.yaml      # Generated output
```

### After Extraction (Future)
```
ai-readiness-evaluator/
├── requirements.txt           # Add: api-metadata-analyzer>=1.0.0
├── scripts/
│   └── generate_api_metadata.py   # Thin wrapper
└── config/
    ├── apis.yaml              # Input config (new format)
    └── api_metadata.yaml      # Generated output
```

**Wrapper Script** (`scripts/generate_api_metadata.py`):
```python
#!/usr/bin/env python3
"""
Generate API metadata using the api-metadata-analyzer package.
This is a thin wrapper that adapts our apis.txt format to the analyzer's input.
"""
from api_metadata_analyzer import BatchAnalyzer, AnalyzerConfig
import configparser

# Read our apis.txt format
config = configparser.ConfigParser()
config.read('config/apis.txt')

# Convert to analyzer format
apis = []
for section in config.sections():
    apis.append({
        'name': section,
        'sample_endpoint': extract_url_from_curl(config[section]['curl_command']),
        'documentation_url': config[section]['documentation_url']
    })

# Run analyzer
analyzer_config = AnalyzerConfig(llm_provider="gemini-2.0-flash")
batch = BatchAnalyzer(analyzer_config)
results = batch.analyze(apis, parallel=True)

# Generate output in our format
batch.to_yaml(results, 'config/api_metadata.yaml')
```

## Development Approach

### Issues #53-60: Build In-Tree
- Develop all functionality within `ai-readiness-evaluator`
- Test with real 26 APIs
- Validate accuracy and performance
- Iterate on design

### Issue #61: Prepare for Extraction (NEW)
- Refactor to remove project-specific dependencies
- Create package structure (`setup.py`, `__init__.py`)
- Add CLI entry points
- Update documentation for standalone use
- Create migration guide

### Issue #62: Extract and Publish (NEW)
- Create new repository
- Move code to standalone package
- Publish to PyPI
- Update `ai-readiness-evaluator` to use package
- Verify integration works

## Benefits of Standalone Approach

### For This Project
- ✅ Cleaner separation of concerns
- ✅ Easier to maintain and update
- ✅ Can version independently
- ✅ Reusable for future API additions

### For Community
- ✅ Other projects can use the tool
- ✅ Community contributions improve quality
- ✅ Broader testing and validation
- ✅ Potential for commercial support/services

### For Your Portfolio
- ✅ Standalone open-source project
- ✅ Demonstrates software architecture skills
- ✅ Shows ability to build reusable tools
- ✅ Potential for community adoption

## Success Metrics

### Technical
- 90%+ accuracy on API metadata generation
- <30 seconds per API analysis
- <$0.01 per API cost
- >80% test coverage

### Adoption (Post-Extraction)
- 100+ GitHub stars (6 months)
- 10+ community contributors (1 year)
- 1000+ PyPI downloads/month (1 year)
- Used by 5+ other projects (1 year)

## Next Steps

1. **Complete Issues #53-60** - Build and validate in-tree
2. **Create Issues #61-62** - Extraction and publishing
3. **Extract to standalone repo** - After validation
4. **Publish to PyPI** - Make publicly available
5. **Promote and grow** - Community engagement


