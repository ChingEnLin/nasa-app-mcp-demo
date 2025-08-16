"""
Basic MCP integration tests.

This module contains simple tests to verify MCP server integration
works correctly and doesn't break existing functionality.
"""

import os
import pytest
from fastapi.testclient import TestClient


def test_mcp_disabled_functionality():
    """Test that app works correctly when MCP is disabled."""
    # Set environment to disable MCP
    os.environ['NASA_MCP_ENABLE_MCP'] = 'false'
    
    # Import after setting environment variable
    from nasa_mcp_demo.main import app
    
    with TestClient(app) as client:
        # Test basic endpoints work
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "NASA Data API"
        assert "mcp_integration" not in data
        
        # Test MCP status endpoint
        response = client.get("/mcp/status")
        assert response.status_code == 200
        data = response.json()
        assert data["mcp_enabled"] is False
        assert data["mcp_initialized"] is False


def test_mcp_enabled_functionality():
    """Test that app works correctly when MCP is enabled."""
    # Set environment to enable MCP
    os.environ['NASA_MCP_ENABLE_MCP'] = 'true'
    
    # Need to reload the module to pick up new environment variable
    import importlib
    import nasa_mcp_demo.main
    importlib.reload(nasa_mcp_demo.main)
    from nasa_mcp_demo.main import app
    
    with TestClient(app) as client:
        # Test basic endpoints still work
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "NASA Data API"
        assert "mcp_integration" in data
        assert data["mcp_integration"]["enabled"] is True
        assert data["mcp_integration"]["initialized"] is True
        
        # Test MCP status endpoint
        response = client.get("/mcp/status")
        assert response.status_code == 200
        data = response.json()
        assert data["mcp_enabled"] is True
        assert data["mcp_initialized"] is True
        assert "server_info" in data
        assert data["server_info"]["enabled"] is True


def test_existing_endpoints_unchanged():
    """Test that existing endpoints are unchanged by MCP integration."""
    os.environ['NASA_MCP_ENABLE_MCP'] = 'true'
    
    # Need to reload the module to pick up new environment variable
    import importlib
    import nasa_mcp_demo.main
    importlib.reload(nasa_mcp_demo.main)
    from nasa_mcp_demo.main import app
    
    with TestClient(app) as client:
        # Test that all original endpoints are still available
        original_endpoints = [
            "/",
            "/health",
            "/rovers"
        ]
        
        for endpoint in original_endpoints:
            response = client.get(endpoint)
            # Should not return 404 (endpoint exists)
            assert response.status_code != 404
        
        # Test that API structure is preserved
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        
        # Original fields should still be present
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "endpoints" in data
        assert "nasa_apis" in data
        
        # Original endpoints should still be listed
        endpoints = data["endpoints"]
        assert "apod" in endpoints
        assert "mars_photos" in endpoints
        assert "neo" in endpoints
        assert "health" in endpoints
        assert "docs" in endpoints