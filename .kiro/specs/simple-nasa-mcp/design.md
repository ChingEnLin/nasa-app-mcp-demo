# Design Document

## Overview

A minimal FastAPI application with MCP integration. The design prioritizes simplicity and clarity over comprehensive features. The application will have a single main file with NASA API integration and MCP tools.

## Architecture

```
simple-nasa-mcp/
├── main.py              # Single FastAPI app with MCP integration
├── requirements.txt     # Dependencies
├── .env                # NASA API key
└── README.md           # Basic setup instructions
```

## Components and Interfaces

### FastAPI Application
- Single `main.py` file containing the entire application
- FastAPI instance with basic configuration
- Three REST endpoints: `/apod`, `/mars-photos`, `/neo`
- Health check endpoint at `/health`

### NASA API Integration
- Simple httpx client for NASA API calls
- Direct API calls without complex abstraction layers
- Basic error handling for API failures

### MCP Integration
- Use `fastapi_mcp` library to add MCP server capabilities
- Three MCP tools matching the REST endpoints:
  - `get_astronomy_picture` - APOD data
  - `search_mars_rover_photos` - Mars rover images
  - `find_near_earth_objects` - NEO data

## Data Models

### Simple Response Models
- Use basic Pydantic models for API responses
- Minimal validation, focus on core data structure
- No complex nested models or extensive validation

### Configuration
- Environment variables for NASA API key
- Simple configuration without complex settings management

## Error Handling

### Basic Error Responses
- HTTP status codes for REST endpoints
- Simple error messages for MCP tools
- Graceful handling of NASA API unavailability

## Testing Strategy

### Minimal Testing
- Single test file with basic endpoint tests
- Mock NASA API responses for testing
- No extensive test suites or complex scenarios