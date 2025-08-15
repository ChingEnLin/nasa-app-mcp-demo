#!/usr/bin/env python3
"""
Development server runner for NASA MCP Demo.

This script starts the FastAPI development server with proper configuration.
"""

import uvicorn
from nasa_mcp_demo.models.config import AppConfig

if __name__ == "__main__":
    # Load configuration
    config = AppConfig()
    
    print(f"Starting NASA MCP Demo server...")
    print(f"Server will be available at: http://{config.host}:{config.port}")
    print(f"API documentation: http://{config.host}:{config.port}/docs")
    print(f"Debug mode: {config.debug}")
    print(f"NASA API key: {'DEMO_KEY' if config.is_demo_mode() else 'Custom key configured'}")
    
    # Start the server
    uvicorn.run(
        "nasa_mcp_demo.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level=config.logging.level.lower(),
        access_log=config.logging.enable_request_logging
    )