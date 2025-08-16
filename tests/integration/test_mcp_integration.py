"""
Integration tests for MCP server integration.

This module tests that MCP integration doesn't break existing functionality
and that MCP server is properly initialized when enabled.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from nasa_mcp_demo.main import app
from nasa_mcp_demo.models.config import AppConfig


class TestMCPIntegration:
    """Test MCP server integration with existing FastAPI app."""
    
    def test_existing_endpoints_work_with_mcp_disabled(self):
        """Test that all existing endpoints work when MCP is disabled."""
        with patch('nasa_mcp_demo.main.AppConfig') as mock_config_class:
            with patch('nasa_mcp_demo.main.setup_logging'):
                # Configure mock to disable MCP
                mock_config = MagicMock(spec=AppConfig)
                mock_config.enable_mcp = False
                mock_config.app_name = "NASA MCP Demo"
                mock_config.app_version = "1.0.0"
                mock_config.debug = True
                mock_config.mcp_server_name = "nasa-mcp-demo"
                mock_config.cors_origins = ["*"]
                mock_config.cors_allow_credentials = True
                mock_config.cors_allow_methods = ["*"]
                mock_config.cors_allow_headers = ["*"]
                
                # Mock logging config
                mock_logging = MagicMock()
                mock_config.logging = mock_logging
                mock_config_class.return_value = mock_config
            
            with TestClient(app) as client:
                # Test root endpoint
                response = client.get("/")
                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "NASA Data API"
                assert "mcp_integration" not in data
                
                # Test health endpoint
                response = client.get("/health")
                assert response.status_code in [200, 503]  # May fail due to NASA API
                
                # Test MCP status endpoint
                response = client.get("/mcp/status")
                assert response.status_code == 200
                data = response.json()
                assert data["mcp_enabled"] is False
                assert data["mcp_initialized"] is False
    
    def test_existing_endpoints_work_with_mcp_enabled(self):
        """Test that all existing endpoints work when MCP is enabled."""
        with patch('nasa_mcp_demo.main.AppConfig') as mock_config_class:
            with patch('nasa_mcp_demo.main.create_mcp_server') as mock_create_mcp:
                with patch('nasa_mcp_demo.main.setup_logging'):
                    # Configure mock to enable MCP
                    mock_config = MagicMock(spec=AppConfig)
                    mock_config.enable_mcp = True
                    mock_config.app_name = "NASA MCP Demo"
                    mock_config.app_version = "1.0.0"
                    mock_config.debug = True
                    mock_config.mcp_server_name = "nasa-mcp-demo"
                    mock_config.cors_origins = ["*"]
                    mock_config.cors_allow_credentials = True
                    mock_config.cors_allow_methods = ["*"]
                    mock_config.cors_allow_headers = ["*"]
                    
                    # Mock logging config
                    mock_logging = MagicMock()
                    mock_config.logging = mock_logging
                    mock_config_class.return_value = mock_config
                
                # Mock MCP server
                mock_mcp_server = MagicMock()
                mock_mcp_server.is_enabled.return_value = True
                mock_mcp_server.get_server_info.return_value = {
                    "enabled": True,
                    "server_name": "nasa-mcp-demo",
                    "version": "1.0.0",
                    "description": "NASA data access through MCP protocol",
                    "tools_available": 0,
                    "protocol_version": "1.0"
                }
                mock_create_mcp.return_value = mock_mcp_server
                
                with TestClient(app) as client:
                    # Test root endpoint includes MCP info
                    response = client.get("/")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["name"] == "NASA Data API"
                    assert "mcp_integration" in data
                    assert data["mcp_integration"]["enabled"] is True
                    
                    # Test health endpoint still works
                    response = client.get("/health")
                    assert response.status_code in [200, 503]  # May fail due to NASA API
                    
                    # Test MCP status endpoint
                    response = client.get("/mcp/status")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["mcp_enabled"] is True
                    assert data["mcp_initialized"] is True
    
    def test_mcp_server_initialization_failure_doesnt_break_app(self):
        """Test that MCP server initialization failure doesn't break the app."""
        with patch('nasa_mcp_demo.main.AppConfig') as mock_config_class:
            with patch('nasa_mcp_demo.main.create_mcp_server') as mock_create_mcp:
                with patch('nasa_mcp_demo.main.setup_logging'):
                    # Configure mock to enable MCP
                    mock_config = MagicMock(spec=AppConfig)
                    mock_config.enable_mcp = True
                    mock_config.app_name = "NASA MCP Demo"
                    mock_config.app_version = "1.0.0"
                    mock_config.debug = True
                    mock_config.mcp_server_name = "nasa-mcp-demo"
                    mock_config.cors_origins = ["*"]
                    mock_config.cors_allow_credentials = True
                    mock_config.cors_allow_methods = ["*"]
                    mock_config.cors_allow_headers = ["*"]
                    
                    # Mock logging config
                    mock_logging = MagicMock()
                    mock_config.logging = mock_logging
                    mock_config_class.return_value = mock_config
                
                # Make MCP server creation fail
                mock_create_mcp.side_effect = Exception("MCP initialization failed")
                
                with TestClient(app) as client:
                    # App should still work
                    response = client.get("/")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["name"] == "NASA Data API"
                    
                    # MCP status should show failure
                    response = client.get("/mcp/status")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["mcp_enabled"] is True
                    assert data["mcp_initialized"] is False
    
    def test_mcp_status_endpoint_structure(self):
        """Test MCP status endpoint returns correct structure."""
        with patch('nasa_mcp_demo.main.AppConfig') as mock_config_class:
            with patch('nasa_mcp_demo.main.setup_logging'):
                mock_config = MagicMock(spec=AppConfig)
                mock_config.enable_mcp = False
                mock_config.mcp_server_name = "nasa-mcp-demo"
                
                # Mock logging config
                mock_logging = MagicMock()
                mock_config.logging = mock_logging
                mock_config_class.return_value = mock_config
            
            with TestClient(app) as client:
                response = client.get("/mcp/status")
                assert response.status_code == 200
                data = response.json()
                
                # Check required fields
                assert "timestamp" in data
                assert "mcp_enabled" in data
                assert "mcp_initialized" in data
                assert "server_info" in data
                assert "configuration" in data
                
                # Check configuration structure
                config_data = data["configuration"]
                assert "enable_mcp" in config_data
                assert "mcp_server_name" in config_data
    
    def test_existing_api_endpoints_unchanged(self):
        """Test that existing API endpoints are unchanged by MCP integration."""
        with patch('nasa_mcp_demo.main.AppConfig') as mock_config_class:
            with patch('nasa_mcp_demo.main.setup_logging'):
                mock_config = MagicMock(spec=AppConfig)
                mock_config.enable_mcp = True
                mock_config.app_name = "NASA MCP Demo"
                mock_config.app_version = "1.0.0"
                mock_config.debug = True
                mock_config.mcp_server_name = "nasa-mcp-demo"
                mock_config.cors_origins = ["*"]
                mock_config.cors_allow_credentials = True
                mock_config.cors_allow_methods = ["*"]
                mock_config.cors_allow_headers = ["*"]
                
                # Mock logging config
                mock_logging = MagicMock()
                mock_config.logging = mock_logging
                mock_config_class.return_value = mock_config
            
            with TestClient(app) as client:
                # Test that all original endpoints are still available
                original_endpoints = [
                    "/",
                    "/health",
                    "/rovers",
                    "/metrics"
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


class TestMCPServerClass:
    """Test the NASAMCPServer class directly."""
    
    def test_mcp_server_creation_disabled(self):
        """Test MCP server creation when disabled."""
        from nasa_mcp_demo.mcp_server import NASAMCPServer
        from fastapi import FastAPI
        
        app = FastAPI()
        config = MagicMock()
        config.enable_mcp = False
        config.mcp_server_name = "test-server"
        nasa_service = MagicMock()
        
        mcp_server = NASAMCPServer(app, config, nasa_service)
        
        assert not mcp_server.is_enabled()
        assert mcp_server.mcp_server is None
        
        server_info = mcp_server.get_server_info()
        assert server_info["enabled"] is False
        assert "reason" in server_info
    
    def test_mcp_server_creation_enabled(self):
        """Test MCP server creation when enabled."""
        from nasa_mcp_demo.mcp_server import NASAMCPServer
        from fastapi import FastAPI
        
        with patch('nasa_mcp_demo.mcp_server.FastApiMCP') as mock_mcp_server_class:
            mock_mcp_server = MagicMock()
            mock_mcp_server_class.return_value = mock_mcp_server
            
            app = FastAPI()
            config = MagicMock()
            config.enable_mcp = True
            config.mcp_server_name = "test-server"
            nasa_service = MagicMock()
            
            mcp_server = NASAMCPServer(app, config, nasa_service)
            
            assert mcp_server.is_enabled()
            assert mcp_server.mcp_server is not None
            
            # Verify MCP server was created with correct parameters
            mock_mcp_server_class.assert_called_once_with(
                name="test-server",
                description="NASA data access through MCP protocol"
            )
            
            # Verify integration with FastAPI app
            mock_mcp_server.init_app.assert_called_once_with(app)
            
            server_info = mcp_server.get_server_info()
            assert server_info["enabled"] is True
            assert server_info["server_name"] == "test-server"
    
    def test_create_mcp_server_factory(self):
        """Test the create_mcp_server factory function."""
        from nasa_mcp_demo.mcp_server import create_mcp_server, NASAMCPServer
        from fastapi import FastAPI
        
        app = FastAPI()
        config = MagicMock()
        config.enable_mcp = False
        nasa_service = MagicMock()
        
        mcp_server = create_mcp_server(app, config, nasa_service)
        
        assert isinstance(mcp_server, NASAMCPServer)
        assert mcp_server.app is app
        assert mcp_server.config is config
        assert mcp_server.nasa_service is nasa_service