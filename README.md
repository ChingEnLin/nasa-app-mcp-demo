# NASA MCP Demo

Educational demonstration of integrating MCP (Model Context Protocol) capabilities with a FastAPI backend that connects to NASA's public APIs.

## Project Structure

```
nasa-mcp-demo/
├── nasa_mcp_demo/           # Main application package
│   ├── __init__.py
│   ├── config.py            # Configuration management
│   ├── logging_config.py    # Logging setup
│   ├── models/              # Data models
│   │   └── __init__.py
│   ├── services/            # Business logic layer
│   │   └── __init__.py
│   └── clients/             # External API clients
│       └── __init__.py
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── unit/                # Unit tests
│   │   └── __init__.py
│   ├── integration/         # Integration tests
│   │   └── __init__.py
│   └── fixtures/            # Test fixtures
│       └── __init__.py
├── pyproject.toml           # Project configuration
├── .env.example             # Environment variables template
└── README.md               # This file
```

## Setup

1. **Clone and navigate to the project:**
   ```bash
   cd nasa-mcp-demo
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e .
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your NASA API key (optional, DEMO_KEY works for testing)
   ```

5. **Install development dependencies (optional):**
   ```bash
   pip install -e ".[dev]"
   ```

## NASA API Key

This demo works with NASA's DEMO_KEY by default, which has rate limits but requires no registration. For production use or higher rate limits, get a free API key from: https://api.nasa.gov/

## Next Steps

This is the foundation setup. The application will be built incrementally following the implementation plan in `.kiro/specs/nasa-mcp-demo/tasks.md`.

## Development

- **Run tests:** `pytest`
- **Code formatting:** `black .`
- **Linting:** `ruff check .`
- **Type checking:** `mypy nasa_mcp_demo`