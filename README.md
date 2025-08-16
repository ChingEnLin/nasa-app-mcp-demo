# Simple NASA MCP Server

A minimal FastAPI server that provides NASA data through both REST endpoints and MCP (Model Context Protocol) integration.

## Features

- **REST API**: Three NASA data endpoints with OpenAPI documentation
- **MCP Integration**: AI tools can access NASA data through MCP protocol
- **Simple Setup**: Single file implementation with minimal configuration

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure NASA API Key (Optional)

```bash
cp .env.example .env
# Edit .env and replace DEMO_KEY with your NASA API key from https://api.nasa.gov/
```

### 3. Run the Server

```bash
python main.py
```

The server starts at http://localhost:8000

## API Endpoints

- **GET /health** - Health check
- **GET /apod** - Astronomy Picture of the Day
- **GET /mars-photos** - Mars rover photos
- **GET /neo** - Near Earth Objects
- **GET /docs** - Interactive API documentation

## Usage Examples

### REST API

```bash
# Get today's astronomy picture
curl http://localhost:8000/apod

# Get Mars rover photos
curl "http://localhost:8000/mars-photos?rover=curiosity&sol=1000"

# Get near earth objects
curl "http://localhost:8000/neo?start_date=2024-01-01&end_date=2024-01-07"
```

### MCP Integration

The server automatically exposes MCP tools that AI clients can use:

- `get_astronomy_picture` - Get APOD data
- `search_mars_rover_photos` - Get Mars rover images  
- `find_near_earth_objects` - Get NEO data

## NASA API Key

The server works with NASA's DEMO_KEY (1000 requests/hour) by default. For production use:

1. Get a free API key at https://api.nasa.gov/
2. Copy `.env.example` to `.env`
3. Replace `DEMO_KEY` with your API key

## Testing

Run the basic test to verify functionality:

```bash
python test_basic.py
```

## Project Structure

```
simple-nasa-mcp/
├── main.py              # Complete FastAPI application
├── requirements.txt     # Dependencies
├── .env.example        # Environment template
├── test_basic.py       # Basic functionality test
└── README.md           # This file
```