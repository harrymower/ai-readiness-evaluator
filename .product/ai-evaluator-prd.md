## Overview

A Python CLI application that automates testing Claude's ability to build functioning CLI tools against API endpoints using the Claude Agent SDK. The hypothesis is that the more and better-structured information provided to Claude, the better the results will be. The goal is to identify which types of information (curl commands, API documentation, Postman collections, example prompts) are most effective for AI-assisted code generation.

### Recommended Test APIs

Two public APIs have been selected for initial testing:

1. **Open-Meteo Weather API** (https://open-meteo.com/)
   - No authentication required
   - Well-documented with clear examples
   - Returns structured JSON weather data
   - Multiple endpoints for different use cases
   - Ideal for building a CLI tool that fetches weather forecasts

2. **SWAPI - Star Wars API** (https://swapi.dev/)
   - No authentication required
   - Comprehensive documentation
   - Returns structured JSON data about Star Wars universe
   - Multiple endpoints (people, planets, films, species, etc.)
   - Ideal for building a CLI tool that searches for Star Wars data

## Testing Methodology

The application runs multiple rounds of testing, each round progressively adding more information context to Claude:

1. **Round 1**: Curl command only
2. **Round 2**: Curl command + API documentation
3. **Round 3**: Curl command + API documentation + Postman collection
4. **Round 4**: Curl command + API documentation + Postman collection + example prompt

Each round consists of two phases:
- **Working Phase**: Claude generates a CLI tool and tests using the provided information
- **Testing Phase**: The generated CLI tool and tests are executed locally, evaluated, and scored

Results are compared across rounds to determine which information types are most effective.


## Application Architecture

### Folder Structure

```
ai-readiness-evaluator/
├── .product/                          # Product documentation
│   └── ai-evaluator-prd.md           # Product Requirements Document
│
├── ai_evaluator/                      # Main application package
│   ├── __init__.py
│   ├── main.py                        # Entry point / CLI orchestrator
│   ├── config.py                      # Environment & config loading
│   ├── claude_client.py               # Claude SDK integration & session management
│   ├── evaluator.py                   # Evaluation logic & scoring
│   ├── test_runner.py                 # Pytest execution & result parsing
│   ├── report_generator.py            # Report generation (evaluation & comparison)
│   └── utils.py                       # Utility functions (file I/O, parsing, etc.)
│
├── config/                            # Configuration files
│   ├── apis.txt                       # API endpoints and curl commands
│   └── prompts.txt                    # Prompts for each round
│
├── resources/                         # External resources (optional reference)
│   ├── documentation/                 # API documentation (for reference)
│   ├── postman_collections/           # Postman collections (for reference)
│   └── examples/                      # Example prompts (for reference)
│
├── results/                           # Output directory (generated during runs)
│   ├── round_1_curl_only/
│   ├── round_2_with_docs/
│   ├── round_3_with_postman/
│   ├── round_4_with_examples/
│   └── comparison_report.json
│
├── tests/                             # Tests for the evaluator itself
│   ├── __init__.py
│   ├── test_evaluator.py
│   ├── test_test_runner.py
│   └── test_report_generator.py
│
├── .env                               # Environment variables (LOCAL ONLY - DO NOT COMMIT)
├── .env.example                       # Example environment variables (COMMIT THIS)
├── .gitignore                         # Git ignore file
├── README.md                          # Project documentation
├── requirements.txt                   # Python dependencies
└── setup.py                           # Package setup (optional)
```

### Module Responsibilities

- **main.py**: Orchestrates the entire workflow (4 rounds, each with working + testing phases)
- **config.py**: Loads and validates environment variables and configuration
- **claude_client.py**: Handles Claude SDK integration, session management, prompt sending
- **evaluator.py**: Implements the scoring system and evaluation logic
- **test_runner.py**: Executes pytest, parses JSON output, captures results
- **report_generator.py**: Generates evaluation reports and final comparison report
- **utils.py**: Helper functions for file I/O, config parsing, etc.

## Detailed Specifications

### API Endpoints and Curl Commands File

- **Format**: Plain text file
- **Structure**: One API endpoint definition per section, with the following format:
  ```
  [API_NAME]
  curl_command: <full curl command demonstrating API usage>
  description: <brief description of what the API does>
  ```
- **Content**: Contains all API endpoints to be tested across rounds
- **Path**: Hardcoded for now (can be made configurable later)
- **Example**:
  ```
  [OPEN_METEO_WEATHER]
  curl_command: curl -X GET "https://api.open-meteo.com/v1/forecast?latitude=51.5074&longitude=-0.1278&current=temperature_2m,weather_code&timezone=auto"
  description: Retrieves current weather forecast for London using Open-Meteo API

  [SWAPI_PEOPLE]
  curl_command: curl -X GET "https://swapi.dev/api/people/1/"
  description: Retrieves Star Wars character data from SWAPI
  ```

### Prompt File Format

- **Format**: Plain text file
- **Structure**: One prompt per API endpoint, organized by round
- **Path**: Hardcoded for now (can be made configurable later)
- **Prompt Template Structure**: Each prompt includes:
  - Instructions for Claude to build a CLI tool
  - The curl command demonstrating API usage
  - Round-specific information (documentation, Postman collection, example prompt)
  - Instructions to also generate tests for the CLI tool
- **Prompt Variations by Round**:
  - **Round 1**: "Build a CLI tool that calls this API: [CURL_COMMAND]. Also write tests for your CLI tool."
  - **Round 2**: "Build a CLI tool that calls this API: [CURL_COMMAND]. Here is the API documentation: [DOCUMENTATION_URL]. Also write tests for your CLI tool."
  - **Round 3**: "Build a CLI tool that calls this API: [CURL_COMMAND]. Here is the API documentation: [DOCUMENTATION_URL]. Here is a Postman collection: [POSTMAN_COLLECTION_URL]. Also write tests for your CLI tool."
  - **Round 4**: "Build a CLI tool that calls this API: [CURL_COMMAND]. Here is the API documentation: [DOCUMENTATION_URL]. Here is a Postman collection: [POSTMAN_COLLECTION_URL]. Here is an example of how to use the API: [EXAMPLE_PROMPT_URL]. Also write tests for your CLI tool."

### Information Delivery Method

- **Documentation and Collections**: Provided as URLs that Claude will fetch
  - Claude is instructed to fetch and read documentation from provided URLs
  - Postman collections are provided as URLs (JSON format)
  - Example prompts are provided as URLs
  - This allows for flexible, external management of these resources

### Response/Output Format
- **Format**: Directory structure containing generated code, tests, transcripts, and evaluation reports
- **Structure**: Each test run gets a unique numbered folder (test-001, test-002, etc.) to prevent file overwrites. Within each test run:
  - For each round and API combination, a folder is created with:
    - `cli_tool.py`: The generated CLI tool
    - `test_cli_tool.py`: The generated tests
    - `evaluation_report.json`: Evaluation results for this specific API/round combination
    - `working_transcript.md`: Markdown transcript of the working phase (Claude interaction)
    - `testing_transcript.md`: Markdown transcript of the testing phase (test execution and evaluation)
- **Path**: Hardcoded for now (can be made configurable later)
- **Example**:
  ```
  results/
  ├── test-001/
  │   ├── round-1-curl-only/
  │   │   ├── open-meteo-weather/
  │   │   │   ├── cli_tool.py
  │   │   │   ├── test_cli_tool.py
  │   │   │   ├── evaluation_report.json
  │   │   │   ├── working_transcript.md
  │   │   │   └── testing_transcript.md
  │   │   ├── swapi-people/
  │   │   │   ├── cli_tool.py
  │   │   │   ├── test_cli_tool.py
  │   │   │   ├── evaluation_report.json
  │   │   │   ├── working_transcript.md
  │   │   │   └── testing_transcript.md
  │   ├── round-2-with-docs/
  │   │   ├── open-meteo-weather/
  │   │   │   ├── cli_tool.py
  │   │   │   ├── test_cli_tool.py
  │   │   │   ├── evaluation_report.json
  │   │   │   ├── working_transcript.md
  │   │   │   └── testing_transcript.md
  │   │   ├── swapi-people/
  │   │   │   ├── cli_tool.py
  │   │   │   ├── test_cli_tool.py
  │   │   │   ├── evaluation_report.json
  │   │   │   ├── working_transcript.md
  │   │   │   └── testing_transcript.md
  │   ├── round-3-with-postman/
  │   ├── round-4-with-examples/
  │   └── comparison_report.md
  ├── test-002/
  │   └── [same structure as test-001]
  └── comparison_report.md (latest test run)
  ```

### Transcript Formats

#### Working Phase Transcript (`working_transcript.md`)
- **Purpose**: Captures the Claude interaction during code generation
- **Content**:
  - Timestamp of execution
  - Full prompt sent to Claude
  - Claude's complete response (preview)
  - Tool use details (which files were created)

#### Testing Phase Transcript (`testing_transcript.md`)
- **Purpose**: Captures test execution and evaluation results
- **Content**:
  - Timestamp of execution
  - Test execution results (passed, failed, errors, total)
  - Evaluation results (score, pass rate, reasoning)

### Claude Agent SDK Integration
- **SDK**: Claude Agent SDK for Python (`claude-agent-sdk`)
- **Authentication**: Uses Claude Code CLI authentication (assumed to be already configured)
- **Session Management**: Each round has an isolated session
  - Each round (working phase) starts a fresh conversation with Claude
  - No context carries over between rounds
  - Uses `ClaudeSDKClient` async context manager to maintain conversation state within a round
- **Timeout**: 3 minutes maximum wait time for each response
- **MCP Integration**: Supports MemNexus MCP server for memory operations
  - Uses `permission_mode="bypassPermissions"` to auto-approve all tool usage

### Scoring System
The evaluation scoring system uses a gradient-based approach to measure CLI tool quality:

- **100% Success**: Code works as expected
  - CLI tool executes without errors
  - All tests pass
  - Output matches expected format
  - No runtime exceptions

- **Partial Success (Gradient)**:
  - **80-99%**: Minor issues
    - Code runs but has minor bugs or edge case failures
    - Most tests pass (90%+ pass rate)
    - Output is mostly correct with minor formatting issues
  - **60-79%**: Moderate issues
    - Code runs but has significant bugs
    - Some tests pass (50-89% pass rate)
    - Output is partially correct or incomplete
  - **40-59%**: Major issues
    - Code runs but fails on most test cases
    - Few tests pass (10-49% pass rate)
    - Output is significantly incorrect or malformed
  - **20-39%**: Critical issues
    - Code has syntax errors or fails to run
    - Tests don't execute or all fail
    - Output is missing or completely incorrect
    - CLI tool cannot be invoked

- **0% Success**: Code does not work
  - Code has syntax errors and cannot be parsed
  - CLI tool cannot be executed at all
  - No output is produced

**Evaluation Criteria**:
1. **Functionality**: Does the CLI tool correctly call the API and handle responses?
2. **Test Coverage**: Do the generated tests adequately cover the CLI tool's functionality?
3. **Error Handling**: Does the CLI tool handle errors gracefully?
4. **Code Quality**: Is the code well-structured and maintainable?
5. **Completeness**: Does the CLI tool implement all required features from the prompt?

### Test Framework

- **Framework**: pytest
- **Rationale**: Industry standard, well-documented, easy to parse output, supports fixtures and parametrization
- **Generated Tests**: Claude will be instructed to generate tests using pytest
- **Test Execution**: Tests are run using `pytest` command with JSON output format for easy parsing

### Testing Phase

The testing phase executes and evaluates the generated CLI tool and tests locally:

- **Execution Environment**: Local desktop/CLI
- **Test Execution**:
  - Generated tests are executed using pytest
  - CLI tool is invoked with test inputs to verify functionality
  - All output and errors are captured
  - Test results are parsed from pytest JSON output
- **Evaluation Process**:
  - The evaluator runs as a Python CLI application
  - Executes the generated code and tests
  - Evaluates the generated code against the scoring criteria
  - Produces a score (0-100%) based on the gradient system
  - Generates a detailed evaluation report including:
    - Pass/fail status for each test
    - Any runtime errors or exceptions
    - Code quality observations
    - Overall score and reasoning
- **Output**: Evaluation results are stored in the round's output folder as `evaluation_report.json`

### Dependency Management

- **Generated Code Dependencies**:
  - Claude will be instructed to use only Python standard library when possible
  - If external libraries are needed, Claude will generate a `requirements.txt` file
  - The evaluator will automatically install dependencies from `requirements.txt` before running tests
  - If installation fails, the evaluation will fail with a clear error message
- **Evaluator Dependencies**:
  - pytest (for running tests)
  - requests (for fetching URLs)
  - Other standard Python libraries

### Final Comparison Report

- **Trigger**: Generated after all 4 rounds complete successfully
- **Format**: Markdown file named `comparison_report.md` in the test run directory and results root directory
- **Content**:
  - Executive summary of test run
  - Summary scores for each round (average across all APIs)
  - Per-API breakdown of scores across rounds
  - Overview analysis of which information types were most effective
  - Analysis of which round produced the best results
  - Recommendations on information types to prioritize
  - Links to all transcript logs and detailed evaluation reports
- **Location**:
  - `results/test-###/comparison_report.md` (within the test run)
  - `results/comparison_report.md` (latest test run, for quick access)

### Error Handling

- **Behavior**: Terminate on any error
- **Requirements**: Provide clear error message before terminating
- **Error Scenarios**:
  - API endpoints file doesn't exist or is malformed
  - Prompt file doesn't exist or is malformed
  - Claude SDK fails for any prompt
  - Timeout exceeded (3 minutes)
  - Unable to write to response folder
  - Generated code cannot be executed (syntax errors, missing dependencies)
  - Test execution fails

### Configuration

- **File Paths**: Configurable via environment variables (see Environment Configuration section)
- **Logging**: No logging required
- **Output**: Only error messages when errors occur

## Environment Configuration

### Environment Variables

The application uses environment variables for configuration. These are loaded from a `.env` file in the project root.

**Required Environment Variables**:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `OPENAI_API_KEY` | OpenAI API key (for evaluation if needed) | None | `sk-proj-xxxxx` |
| `APIS_CONFIG_FILE` | Path to API endpoints configuration file | `config/apis.txt` | `config/apis.txt` |
| `PROMPTS_CONFIG_FILE` | Path to prompts configuration file | `config/prompts.txt` | `config/prompts.txt` |
| `RESULTS_DIR` | Directory to store evaluation results | `results` | `results` |
| `CLAUDE_TIMEOUT_SECONDS` | Timeout for Claude SDK responses (seconds) | `180` | `180` |
| `CLAUDE_MODEL` | Claude model to use | `claude-3-5-sonnet-20241022` | `claude-3-5-sonnet-20241022` |
| `DEBUG_MODE` | Enable debug mode for verbose output | `false` | `false` |

### .env File

- **Location**: Project root directory (`.env`)
- **Format**: Key=Value pairs, one per line
- **Git Status**: Should NOT be committed (add to `.gitignore`)
- **Purpose**: Store sensitive API keys and local configuration

### .env.example File

- **Location**: Project root directory (`.env.example`)
- **Format**: Template showing all available environment variables
- **Git Status**: SHOULD be committed to repository
- **Purpose**: Provides template for developers to create their own `.env` file

### Configuration Loading

- **Method**: `python-dotenv` package loads `.env` file at application startup
- **Validation**: Application validates all required configuration is present before running
- **Error Handling**: Clear error messages if configuration is missing or invalid

### Claude Authentication

- **Method**: Claude Code CLI authentication (separate from environment variables)
- **Setup**: User must run `claude auth login` before running the evaluator
- **Storage**: Credentials stored by Claude CLI (not in `.env`)
- **Note**: The Claude Agent SDK uses existing CLI authentication automatically
