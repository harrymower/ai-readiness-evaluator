# GitHub Issues Plan: LLM-Based API Metadata Automation

## Overview

This document outlines the GitHub issues to implement the LLM-based API metadata automation system. Issues are organized into phases for incremental delivery.

## Issue Breakdown

### Phase 1: Foundation & Core Infrastructure (Issues #53-57)

**Issue #53: Set up project structure and dependencies**
- Create `scripts/api_analysis/` module structure
- Add dependencies: `google-generativeai`, `openai`, `anthropic`, `pydantic`, `beautifulsoup4`, `requests`
- Create Pydantic models for metadata schema
- Set up configuration for LLM API keys
- **Estimated effort**: 2-3 hours
- **Dependencies**: None
- **Status**: Open

**Issue #54: Implement programmatic analysis (Stage 1)**
- Create `scripts/api_analysis/programmatic.py`
- Implement curl execution and response capture
- Implement JSON schema depth calculator
- Implement pagination detection
- Implement rate limiting detection from headers
- Add unit tests
- **Estimated effort**: 4-6 hours
- **Dependencies**: Issue #53
- **Status**: Open

**Issue #55: Implement documentation fetcher**
- Create `scripts/api_analysis/documentation_fetcher.py`
- Implement HTML fetching and cleaning
- Implement text extraction (strip HTML, keep structure)
- Handle common documentation formats (Swagger UI, Markdown, HTML)
- Add error handling for unreachable docs
- Add unit tests
- **Estimated effort**: 3-4 hours
- **Dependencies**: Issue #53
- **Status**: Open

**Issue #56: Implement LLM analyzer (Stage 2)**
- Create `scripts/api_analysis/llm_analyzer.py`
- Implement Gemini 2.0 Flash integration with structured output
- Implement GPT-4o-mini fallback
- Create prompt template for API analysis
- Implement retry logic and error handling
- Add unit tests (with mocked LLM responses)
- **Estimated effort**: 5-7 hours
- **Dependencies**: Issue #53, #55
- **Status**: Open

**Issue #57: Implement validation and merging (Stage 3)**
- Create `scripts/api_analysis/validators.py` and `yaml_generator.py`
- Implement merge logic (programmatic + LLM results)
- Implement cross-validation rules
- Implement confidence filtering
- Implement enum validation
- Implement YAML generation
- Add unit tests
- **Estimated effort**: 3-4 hours
- **Dependencies**: Issue #54, #56
- **Status**: Open

### Phase 2: Core Scripts & Enhancements (Issues #58-59)

**Issue #58: Create analyzer scripts (single + batch)**
- Create `scripts/analyze_api.py` for single API analysis
- Create `scripts/batch_analyze_apis.py` for batch processing
- Implement CLI argument parsing for both
- Integrate all three stages (programmatic, LLM, validation)
- Implement output formats (YAML, JSON, text)
- Implement parallel processing for batch
- Implement diff generation vs. existing metadata
- Add verbose/debug mode and dry-run mode
- Create basic documentation
- Add unit tests
- **Estimated effort**: 6-8 hours
- **Dependencies**: Issue #54, #56, #57
- **Status**: Open

**Issue #59: Add enhancements (OpenAPI + multi-LLM + validation)**
- Add OpenAPI spec auto-discovery and parsing
- Implement Claude 3.5 Sonnet integration
- Add cost tracking per LLM provider
- Create `scripts/validate_metadata.py` for accuracy comparison
- Implement human review report generator
- Implement confidence dashboard
- Add spot-checking tools
- Add unit tests
- **Estimated effort**: 6-8 hours
- **Dependencies**: Issue #55, #56, #58
- **Status**: Open

### Phase 3: Testing & Production Readiness (Issue #60)

**Issue #60: Testing, documentation, and production readiness**
- Add comprehensive integration tests
- Add end-to-end tests with all 26 APIs
- Test error handling and edge cases
- Achieve >80% test coverage
- Create user guide and developer guide
- Add comprehensive docstrings
- Create example outputs
- Update main README
- Add configuration management
- Add structured logging and monitoring
- Optimize performance
- Run validation with existing data
- Document accuracy metrics
- **Estimated effort**: 8-12 hours
- **Dependencies**: All previous issues
- **Status**: Open

### Phase 4: Standalone Extraction (Issues #61-62)

**Issue #61: Prepare for standalone extraction**
- Refactor to remove project-specific dependencies
- Create package structure (`setup.py`, `pyproject.toml`)
- Add CLI entry points
- Create standalone documentation
- Support flexible input/output formats
- Test as standalone package
- Create migration guide
- **Estimated effort**: 4-6 hours
- **Dependencies**: Issue #60
- **Status**: Open

**Issue #62: Extract to standalone repository and publish to PyPI**
- Create new GitHub repository: `api-metadata-analyzer`
- Extract code to new repo
- Rename module: `api_analysis` → `api_metadata_analyzer`
- Publish to PyPI
- Update `ai-readiness-evaluator` to use as dependency
- Create wrapper script for this project
- Set up CI/CD (optional)
- **Estimated effort**: 4-6 hours
- **Dependencies**: Issue #61
- **Status**: Open

## Total Estimated Effort

- **Phase 1**: 17-24 hours (Foundation)
- **Phase 2**: 12-16 hours (Core functionality + enhancements)
- **Phase 3**: 8-12 hours (Testing & documentation)
- **Phase 4**: 8-12 hours (Standalone extraction)
- **Total**: 45-64 hours (~1.5-2 weeks for one developer)

## Phased Delivery

### Minimum Viable Product (MVP)
- Issues #53-58: Core functionality to analyze APIs
- **Deliverable**: Can analyze single API or batch process all APIs
- **Timeline**: ~3-4 days
- **Features**: Programmatic + LLM analysis, validation, YAML output
- **Status**: In-tree development

### Enhanced Version
- Issues #53-59: Add OpenAPI support, multi-LLM, validation workflow
- **Deliverable**: Production-ready with multiple LLM options and quality assurance
- **Timeline**: ~5-6 days
- **Features**: MVP + OpenAPI parsing, Claude support, cost tracking, review workflow
- **Status**: In-tree development

### Complete In-Tree Solution
- Issues #53-60: Full testing and documentation
- **Deliverable**: Fully tested, documented, production-ready (within this project)
- **Timeline**: ~7-9 days
- **Features**: Enhanced + comprehensive tests, guides, examples, validation report
- **Status**: In-tree development

### Standalone Package
- Issues #53-62: Extraction and publishing
- **Deliverable**: Standalone PyPI package + this project uses it as dependency
- **Timeline**: ~9-12 days
- **Features**: Complete solution + standalone package, PyPI published, reusable by community
- **Status**: Standalone repository

## Success Metrics

After implementation, measure:
1. **Accuracy**: % match with existing manual assessments
2. **Speed**: Average time per API
3. **Cost**: Average cost per API
4. **Coverage**: % of fields successfully populated
5. **Confidence**: Average confidence scores

Target: 90%+ accuracy, <30 sec/API, <$0.01/API


