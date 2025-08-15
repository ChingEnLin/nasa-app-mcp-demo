# NASA MCP Demo

Educational demonstration of integrating MCP (Model Context Protocol) capabilities with a FastAPI backend that connects to NASA's public APIs.

## Project Structure

```
nasa-app-mcp-demo/
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

### 1. Clone and navigate to the project
```bash
cd nasa-app-mcp-demo
```

### 2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -e .
```

### 4. Set up environment variables

#### Option A: Use DEMO_KEY (Quick Start)
The application works out of the box with NASA's DEMO_KEY (1000 requests/hour limit):
```bash
# No .env file needed - uses DEMO_KEY by default
python run_server.py
```

#### Option B: Use Custom NASA API Key (Recommended)
For higher rate limits, get a free API key from https://api.nasa.gov/ and configure it:

1. **Get your NASA API key:**
   - Visit https://api.nasa.gov/
   - Click "Generate API Key"
   - Fill out the form (takes 30 seconds)
   - Copy your API key

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Edit the .env file with your API key:**
   ```bash
   # NASA API Configuration (nested under nasa config)
   NASA_MCP_NASA__API_KEY=your_nasa_api_key_here
   NASA_MCP_NASA__BASE_URL=https://api.nasa.gov
   NASA_MCP_NASA__TIMEOUT=30
   NASA_MCP_NASA__MAX_RETRIES=3
   NASA_MCP_NASA__RATE_LIMIT_PER_HOUR=1000

   # Logging Configuration (nested under logging config)
   NASA_MCP_LOGGING__LEVEL=INFO
   NASA_MCP_LOGGING__FORMAT=json

   # Application Configuration
   NASA_MCP_ENABLE_MCP=false
   NASA_MCP_DEBUG=false

   # CORS Configuration (as JSON array)
   NASA_MCP_CORS_ORIGINS=["*"]

   # Server Configuration
   NASA_MCP_HOST=0.0.0.0
   NASA_MCP_PORT=8000
   ```

   **Important:** Replace `your_nasa_api_key_here` with your actual NASA API key.

### 5. Install development dependencies (for testing)
```bash
pip install -e ".[dev]"
```

## Running the Application

### Start the FastAPI Server
```bash
python run_server.py
```

The server will start at http://localhost:8000 with:
- **API Documentation:** http://localhost:8000/docs (Swagger UI)
- **ReDoc Documentation:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

### Test the API
```bash
# Test all endpoints
python example_usage.py

# Or test individual endpoints
curl http://localhost:8000/health
curl http://localhost:8000/apod
curl "http://localhost:8000/mars-photos/curiosity?sol=1000"
```

## NASA API Key Information

### DEMO_KEY (Default)
- **Rate Limit:** 1000 requests per hour
- **No registration required**
- **Good for:** Testing and development
- **Usage:** Automatic (no configuration needed)

### Personal API Key (Recommended)
- **Rate Limit:** 1000 requests per hour (same as DEMO_KEY, but dedicated)
- **Registration:** Free at https://api.nasa.gov/
- **Good for:** Production use, avoiding shared rate limits
- **Usage:** Configure in `.env` file as shown above

## Testing

### Important: Use Virtual Environment
Make sure you're in your virtual environment before running tests:

```bash
# Activate virtual environment
source venv/bin/activate

# Verify you're in the right environment
which python  # Should point to venv/bin/python
```

### Run Tests
```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/unit/ -v                    # Unit tests only
python -m pytest tests/integration/ -v             # Integration tests only

# Run specific test files
python -m pytest tests/integration/test_fastapi_endpoints.py -v

# Run with coverage
python -m pytest --cov=nasa_mcp_demo --cov-report=html
```

### Common Testing Issues

**Problem:** `ModuleNotFoundError: No module named 'fastapi'`
**Solution:** Make sure you're in the virtual environment and have installed dependencies:
```bash
source venv/bin/activate
pip install -e .
python -m pytest  # Use python -m pytest, not just pytest
```

**Problem:** Tests fail with configuration errors
**Solution:** Tests use default configuration, no .env file needed for testing.

## Development

### Code Quality Tools
```bash
# Code formatting
black .

# Linting
ruff check .

# Type checking
mypy nasa_mcp_demo

# Run all quality checks
black . && ruff check . && mypy nasa_mcp_demo
```

### Project Status
This project implements a complete FastAPI application with NASA API integration. See `FASTAPI_IMPLEMENTATION.md` for detailed implementation notes.

## API Endpoints

- **`GET /`** - API information
- **`GET /health`** - Health check with NASA API connectivity
- **`GET /apod`** - Astronomy Picture of the Day
- **`GET /apod?date=YYYY-MM-DD`** - APOD for specific date
- **`GET /mars-photos/{rover}?sol={sol}`** - Mars rover photos
- **`GET /neo?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`** - Near Earth Objects
- **`GET /rovers`** - Available Mars rovers information

## Troubleshooting

### Server Won't Start
1. Check you're in virtual environment: `source venv/bin/activate`
2. Install dependencies: `pip install -e .`
3. Check .env file format (see setup instructions above)
4. Try with DEMO_KEY: remove .env file and run `python run_server.py`

### Tests Fail
1. Activate virtual environment: `source venv/bin/activate`
2. Install dev dependencies: `pip install -e ".[dev]"`
3. Use python module: `python -m pytest` instead of `pytest`

### API Errors
1. Check NASA API status: https://api.nasa.gov/
2. Verify API key in .env file
3. Check rate limits (1000/hour for both DEMO_KEY and personal keys)
4. Check server logs for detailed error messages