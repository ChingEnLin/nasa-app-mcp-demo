"""
Unit tests for MCP tools implementation.

This module tests the MCP server setup and tool registration to ensure they properly
integrate with the NASA service layer and are configured correctly for AI model consumption.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from nasa_mcp_demo.mcp_server import NASAMCPServer
from nasa_mcp_demo.models.config import AppConfig
from nasa_mcp_demo.models.errors import NASAAPIError, NASAAPIInvalidRequest
from fastapi import FastAPI


class TestMCPServerSetup:
    """Unit tests for MCP server setup and tool registration."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration with MCP enabled."""
        config = MagicMock(spec=AppConfig)
        config.enable_mcp = True
        config.mcp_server_name = "test-nasa-mcp"
        return config
    
    @pytest.fixture
    def mock_nasa_service(self):
        """Create mock NASA service."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI app."""
        return MagicMock(spec=FastAPI)
    
    @patch('nasa_mcp_demo.mcp_server.FastApiMCP')
    def test_mcp_server_initialization_with_tools(
        self, 
        mock_mcp_class,
        mock_app,
        mock_config, 
        mock_nasa_service
    ):
        """Test MCP server initialization and tool registration."""
        # Setup mocks
        mock_mcp_instance = MagicMock()
        mock_mcp_class.return_value = mock_mcp_instance
        
        # Create MCP server
        mcp_server = NASAMCPServer(mock_app, mock_config, mock_nasa_service)
        
        # Verify MCP server was created with correct parameters
        mock_mcp_class.assert_called_once_with(
            fastapi=mock_app,
            name="test-nasa-mcp",
            description="NASA data access through MCP protocol"
        )
        
        # Verify FastAPI endpoints were added (3 endpoints should be registered)
        assert mock_app.post.call_count == 3
        
        # Verify server is enabled and has correct tool count
        assert mcp_server.is_enabled()
        assert mcp_server._tools_count == 3
    
    @patch('nasa_mcp_demo.mcp_server.FastApiMCP')
    def test_tool_registration_names_and_descriptions(
        self,
        mock_mcp_class,
        mock_app,
        mock_config,
        mock_nasa_service
    ):
        """Test that MCP endpoints are added to FastAPI app."""
        mock_mcp_instance = MagicMock()
        mock_mcp_class.return_value = mock_mcp_instance
        
        # Create MCP server
        mcp_server = NASAMCPServer(mock_app, mock_config, mock_nasa_service)
        
        # Verify that FastAPI endpoints were added (post method calls)
        post_calls = [call for call in mock_app.post.call_args_list]
        
        # Verify all expected MCP endpoints are registered
        expected_endpoints = [
            '/mcp/tools/get_astronomy_picture',
            '/mcp/tools/search_mars_rover_photos', 
            '/mcp/tools/find_near_earth_objects'
        ]
        
        registered_endpoints = [call[0][0] for call in post_calls]
        
        for endpoint in expected_endpoints:
            assert endpoint in registered_endpoints
        
        # Verify that all endpoints have the MCP Tools tag
        for call in post_calls:
            if len(call) > 1 and 'tags' in call[1]:
                assert "MCP Tools" in call[1]['tags']
    
    def test_mcp_server_disabled(self, mock_app, mock_nasa_service):
        """Test MCP server when disabled in configuration."""
        config = MagicMock(spec=AppConfig)
        config.enable_mcp = False
        config.mcp_server_name = "test-nasa-mcp"
        
        mcp_server = NASAMCPServer(mock_app, config, mock_nasa_service)
        
        # Verify server is not enabled
        assert not mcp_server.is_enabled()
        assert mcp_server.mcp_server is None
        assert mcp_server._tools_count == 0
        
        # Verify server info reflects disabled state
        server_info = mcp_server.get_server_info()
        assert server_info["enabled"] is False
        assert "reason" in server_info
    
    @patch('nasa_mcp_demo.mcp_server.FastApiMCP')
    def test_server_info_with_tools(
        self,
        mock_mcp_class,
        mock_app,
        mock_config,
        mock_nasa_service
    ):
        """Test server info includes correct tool information."""
        mock_mcp_instance = MagicMock()
        mock_mcp_class.return_value = mock_mcp_instance
        
        mcp_server = NASAMCPServer(mock_app, mock_config, mock_nasa_service)
        server_info = mcp_server.get_server_info()
        
        # Verify server info structure
        assert server_info["enabled"] is True
        assert server_info["server_name"] == "test-nasa-mcp"
        assert server_info["tools_available"] == 3
        assert "tools" in server_info
        assert len(server_info["tools"]) == 3
        
        # Verify tool information
        tool_names = [tool["name"] for tool in server_info["tools"]]
        assert "get_astronomy_picture" in tool_names
        assert "search_mars_rover_photos" in tool_names
        assert "find_near_earth_objects" in tool_names
        
        # Verify each tool has a description
        for tool in server_info["tools"]:
            assert "description" in tool
            assert len(tool["description"]) > 0
    
    def test_get_rover_context(self, mock_app, mock_config, mock_nasa_service):
        """Test rover context helper method."""
        with patch('nasa_mcp_demo.mcp_server.FastApiMCP'):
            mcp_server = NASAMCPServer(mock_app, mock_config, mock_nasa_service)
            
            # Test known rovers
            assert "Nuclear-powered rover" in mcp_server._get_rover_context("curiosity")
            assert "searching for signs of ancient microbial life" in mcp_server._get_rover_context("perseverance")
            assert "nearly 15 years" in mcp_server._get_rover_context("opportunity")
            assert "First of the Mars Exploration Rovers" in mcp_server._get_rover_context("spirit")
            
            # Test case insensitivity
            assert "Nuclear-powered rover" in mcp_server._get_rover_context("CURIOSITY")
            
            # Test unknown rover
            context = mcp_server._get_rover_context("unknown_rover")
            assert "Mars exploration rover: unknown_rover" in context
    
    @patch('nasa_mcp_demo.mcp_server.FastApiMCP')
    def test_mcp_server_initialization_failure(
        self,
        mock_mcp_class,
        mock_app,
        mock_config,
        mock_nasa_service
    ):
        """Test MCP server initialization failure handling."""
        # Make FastApiMCP initialization fail
        mock_mcp_class.side_effect = Exception("MCP initialization failed")
        
        # Should raise exception during initialization
        with pytest.raises(Exception) as exc_info:
            NASAMCPServer(mock_app, mock_config, mock_nasa_service)
        
        assert "MCP initialization failed" in str(exc_info.value)


class TestMCPToolsLogic:
    """Test the logic and helper methods used by MCP tools."""
    
    @pytest.fixture
    def mcp_server(self):
        """Create MCP server for testing helper methods."""
        config = MagicMock(spec=AppConfig)
        config.enable_mcp = False  # Disable to avoid MCP setup
        config.mcp_server_name = "test-server"
        
        app = MagicMock(spec=FastAPI)
        nasa_service = AsyncMock()
        
        return NASAMCPServer(app, config, nasa_service)
    
    def test_rover_context_all_rovers(self, mcp_server):
        """Test rover context for all supported rovers."""
        rover_tests = [
            ("curiosity", "Nuclear-powered rover"),
            ("perseverance", "ancient microbial life"),
            ("opportunity", "nearly 15 years"),
            ("spirit", "First of the Mars Exploration Rovers")
        ]
        
        for rover, expected_text in rover_tests:
            context = mcp_server._get_rover_context(rover)
            assert expected_text in context
            
            # Test case insensitivity
            context_upper = mcp_server._get_rover_context(rover.upper())
            assert expected_text in context_upper
    
    def test_rover_context_unknown_rover(self, mcp_server):
        """Test rover context for unknown rover names."""
        unknown_rovers = ["unknown", "test_rover", "mars_rover_x"]
        
        for rover in unknown_rovers:
            context = mcp_server._get_rover_context(rover)
            assert f"Mars exploration rover: {rover}" in context


class TestMCPServerFactory:
    """Test the create_mcp_server factory function."""
    
    def test_create_mcp_server_factory(self):
        """Test the create_mcp_server factory function."""
        from nasa_mcp_demo.mcp_server import create_mcp_server
        
        app = MagicMock(spec=FastAPI)
        config = MagicMock(spec=AppConfig)
        config.enable_mcp = False
        nasa_service = AsyncMock()
        
        mcp_server = create_mcp_server(app, config, nasa_service)
        
        assert isinstance(mcp_server, NASAMCPServer)
        assert mcp_server.app is app
        assert mcp_server.config is config
        assert mcp_server.nasa_service is nasa_service
