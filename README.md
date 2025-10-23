# AI Readiness Evaluator

An automated testing framework that evaluates Claude's ability to build functioning CLI tools against API endpoints using the Claude Agent SDK.

## Overview

This application tests the hypothesis that providing more and better-structured information to Claude improves the quality of generated code. It runs 4 progressive rounds of testing, each adding more context:

1. **Round 1**: Curl command only
2. **Round 2**: Curl command + API documentation
3. **Round 3**: Curl command + API documentation + Postman collection
4. **Round 4**: Curl command + API documentation + Postman collection + example prompt

## Project Structure

```
ai-readiness-evaluator/
├── ai_evaluator/              # Main application package
├── config/                    # Configuration files (APIs, prompts)
├── resources/                 # External resources (documentation, collections)
├── results/                   # Output directory (generated during runs)
├── tests/                     # Unit tests
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Setup

### Prerequisites

- Python 3.8+
- Claude Code CLI authentication configured (`claude auth login`)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-readiness-evaluator
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file from the template:
```bash
cp .env.example .env
```

5. Edit `.env` and add your API keys:
```
OPENAI_API_KEY=your_key_here
```

## Configuration

### Environment Variables

See `.env.example` for all available configuration options:

- `CLAUDE_TIMEOUT_SECONDS`: Timeout for Claude responses (default: 180)
- `CLAUDE_MODEL`: Claude model to use (default: claude-3-5-sonnet-20241022)
- `APIS_CONFIG_FILE`: Path to API endpoints file (default: config/apis.txt)
- `PROMPTS_CONFIG_FILE`: Path to prompts file (default: config/prompts.txt)
- `RESULTS_DIR`: Directory for results (default: results)
- `DEBUG_MODE`: Enable debug output (default: false)

### API Configuration

Edit `config/apis.txt` to add or modify API endpoints to test.

### Prompts Configuration

Edit `config/prompts.txt` to customize the prompts sent to Claude for each round.

## Usage

Run the evaluator:
```bash
python -m ai_evaluator.main
```

Results will be saved to the `results/` directory with the following structure:
```
results/
├── round_1_curl_only/
├── round_2_with_docs/
├── round_3_with_postman/
├── round_4_with_examples/
└── comparison_report.json
```

## Testing

Run the test suite:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=ai_evaluator tests/
```

## Development

### Adding New Modules

1. Create the module in `ai_evaluator/`
2. Add corresponding tests in `tests/`
3. Update this README if needed

### Code Style

- Follow PEP 8
- Use type hints where possible
- Add docstrings to all functions and classes

## Documentation

See `.product/ai-evaluator-prd.md` for the complete Product Requirements Document.

## License

MIT

