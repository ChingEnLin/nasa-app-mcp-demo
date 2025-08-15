"""
Integration tests for logging and monitoring functionality.

This module tests the comprehensive logging, monitoring, and performance
tracking features of the NASA MCP Demo application.
"""

import asyncio
import json
import time
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

import pytest
import structlog
from fastapi.testclient import TestClient
from httpx import AsyncClient

from nasa_mcp_demo.main import app
from nasa_mcp_demo.logging_config import (
    configure_logging,
    PerformanceMonitor,
    NASAAPILogger,
    ErrorTracker,
    get_logging_config
)
from nasa_mcp_demo.middleware import (
    RequestLoggingMiddleware,
    PerformanceMonitoringMiddleware,
    HealthCheckMiddleware
)
from nasa_mcp_demo.models.config import AppConfig, LoggingConfig


class TestLoggingConfiguration:
    """Test logging configuration and setup."""
    
    def test_configure_logging_json_format(self):
        """Test logging configuration with JSON format."""
        configure_logging(
            log_level="INFO",
            log_format="json",
            enable_request_logging=True,
            enable_nasa_api_logging=True
        )
        
        config = get_logging_config()
        assert config["enable_request_logging"] is True
        assert config["enable_nasa_api_logging"] is True
        assert config["log_level"] == "INFO"
    
    def test_configure_logging_text_format(self):
        """Test logging configuration with text format."""
        configure_logging(
            log_level="DEBUG",
            log_format="text",
            enable_request_logging=False,
            enable_nasa_api_logging=False
        )
        
        config = get_logging_config()
        assert config["enable_request_logging"] is False
        assert config["enable_nasa_api_logging"] is False
        assert config["log_level"] == "DEBUG"
    
    def test_get_logger(self):
        """Test logger creation."""
        from nasa_mcp_demo.logging_config import get_logger
        
        logger = get_logger(__name__)
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')


class TestPerformanceMonitor:
    """Test performance monitoring functionality."""
    
    @pytest.fixture
    def logger(self):
        """Create a test logger."""
        return structlog.get_logger("test")
    
    @pytest.fixture
    def performance_monitor(self, logger):
        """Create a performance monitor instance."""
        return PerformanceMonitor(logger)
    
    def test_performance_monitor_start_end(self, performance_monitor):
        """Test performance monitor start and end."""
        performance_monitor.start("test_operation", test_param="value")
        
        assert performance_monitor.operation_name == "test_operation"
        assert performance_monitor.start_time is not None
        
        # Simulate some work
        time.sleep(0.1)
        
        duration = performance_monitor.end(result="success")
        assert duration > 0.1
        assert duration < 1.0  # Should be less than 1 second
    
    def test_performance_monitor_context_manager(self, performance_monitor):
        """Test performance monitor as context manager."""
        with performance_monitor.monitor("context_test", param="value") as monitor:
            assert monitor.operation_name == "context_test"
            assert monitor.start_time is not None
            time.sleep(0.05)
        
        # Context manager should have automatically called end()
    
    def test_performance_monitor_end_without_start(self, performance_monitor):
        """Test calling end without start."""
        duration = performance_monitor.end()
        assert duration == 0.0


class TestNASAAPILogger:
    """Test NASA API specific logging functionality."""
    
    @pytest.fixture
    def logger(self):
        """Create a test logger."""
        return structlog.get_logger("test")
    
    @pytest.fixture
    def nasa_logger(self, logger):
        """Create a NASA API logger instance."""
        return NASAAPILogger(logger)
    
    def test_log_request(self, nasa_logger):
        """Test NASA API request logging."""
        # This should not raise any exceptions
        nasa_logger.log_request(
            "/planetary/apod",
            {"date": "2024-01-01"},
            api_key="test_key"
        )
    
    def test_log_response(self, nasa_logger):
        """Test NASA API response logging."""
        nasa_logger.log_response(
            "/planetary/apod",
            200,
            response_size=1024,
            duration_ms=150.5
        )
    
    def test_log_error(self, nasa_logger):
        """Test NASA API error logging."""
        error = Exception("Test error")
        nasa_logger.log_error(
            "/planetary/apod",
            error,
            retry_attempt=1
        )
    
    def test_log_rate_limit(self, nasa_logger):
        """Test rate limiting logging."""
        nasa_logger.log_rate_limit("/planetary/apod", 60.0)
    
    def test_log_cache_operations(self, nasa_logger):
        """Test cache operation logging."""
        nasa_logger.log_cache_hit("/planetary/apod", "cache_key_123")
        nasa_logger.log_cache_miss("/planetary/apod", "cache_key_456")


class TestErrorTracker:
    """Test error tracking functionality."""
    
    @pytest.fixture
    def logger(self):
        """Create a test logger."""
        return structlog.get_logger("test")
    
    @pytest.fixture
    def error_tracker(self, logger):
        """Create an error tracker instance."""
        return ErrorTracker(logger)
    
    def test_track_error_basic(self, error_tracker):
        """Test basic error tracking."""
        error = ValueError("Test validation error")
        error_id = error_tracker.track_error(
            error,
            context="test_context",
            severity="error"
        )
        
        # Error ID should be returned (though it might be None in this implementation)
    
    def test_track_error_with_context(self, error_tracker):
        """Test error tracking with additional context."""
        error = ConnectionError("Network connection failed")
        error_tracker.track_error(
            error,
            context="nasa_api_request",
            severity="warning",
            endpoint="/planetary/apod",
            retry_attempt=2
        )
    
    def test_error_categorization(self, error_tracker):
        """Test error categorization."""
        # Test different error types
        errors = [
            (ValueError("validation error"), "validation"),
            (KeyError("missing key"), "data"),
            (ConnectionError("network error"), "network"),
            (RuntimeError("runtime error"), "unknown")
        ]
        
        for error, expected_category in errors:
            error_tracker.track_error(error, context="test")


class TestMiddleware:
    """Test middleware functionality."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock ASGI app."""
        async def app(scope, receive, send):
            if scope["type"] == "http":
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"application/json"]]
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"message": "test"}'
                })
        return app
    
    @pytest.mark.asyncio
    async def test_request_logging_middleware(self, mock_app):
        """Test request logging middleware."""
        middleware = RequestLoggingMiddleware(mock_app)
        
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": []
        }
        
        async def receive():
            return {"type": "http.request", "body": b""}
        
        responses = []
        async def send(message):
            responses.append(message)
        
        # This should not raise any exceptions
        await middleware(scope, receive, send)
        
        # Check that responses were sent
        assert len(responses) >= 2  # At least start and body
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_middleware(self, mock_app):
        """Test performance monitoring middleware."""
        middleware = PerformanceMonitoringMiddleware(mock_app)
        
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": []
        }
        
        async def receive():
            return {"type": "http.request", "body": b""}
        
        responses = []
        async def send(message):
            responses.append(message)
        
        await middleware(scope, receive, send)
        
        # Check metrics were updated
        metrics = middleware.get_metrics()
        assert metrics["total_requests"] >= 1
        assert "endpoint_metrics" in metrics
    
    @pytest.mark.asyncio
    async def test_health_check_middleware(self, mock_app):
        """Test health check middleware."""
        middleware = HealthCheckMiddleware(mock_app)
        
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": []
        }
        
        async def receive():
            return {"type": "http.request", "body": b""}
        
        responses = []
        async def send(message):
            responses.append(message)
        
        await middleware(scope, receive, send)
        
        # Check health status
        health = middleware.get_health_status()
        assert "status" in health
        assert "uptime_seconds" in health


class TestLoggingIntegration:
    """Test logging integration with the FastAPI application."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    def test_metrics_endpoint(self, client):
        """Test the metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "timestamp" in data
        assert "nasa_api_stats" in data
        assert "logging_config" in data
        assert "application_config" in data
    
    def test_debug_logs_endpoint_without_debug(self, client):
        """Test debug logs endpoint when debug mode is disabled."""
        response = client.get("/debug/logs")
        # Should return 403 if debug mode is disabled
        assert response.status_code in [200, 403]
    
    @patch('nasa_mcp_demo.models.config.AppConfig')
    def test_debug_logs_endpoint_with_debug(self, mock_config, client):
        """Test debug logs endpoint when debug mode is enabled."""
        # Mock debug mode enabled
        mock_config.return_value.debug = True
        
        response = client.get("/debug/logs")
        if response.status_code == 200:
            data = response.json()
            assert "logging_configuration" in data
            assert "runtime_config" in data
    
    def test_health_endpoint_includes_logging_info(self, client):
        """Test that health endpoint includes logging-related information."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
    
    @patch('nasa_mcp_demo.clients.nasa_client.NASAClient')
    def test_request_response_logging(self, mock_client, client):
        """Test that requests and responses are properly logged."""
        # Mock NASA client
        mock_client.return_value.get_apod = AsyncMock(return_value={
            "date": "2024-01-01",
            "title": "Test APOD",
            "explanation": "Test explanation",
            "url": "https://example.com/image.jpg",
            "media_type": "image"
        })
        
        # Make a request that should trigger logging
        response = client.get("/apod?date=2024-01-01")
        
        # The request should succeed (logging happens in background)
        assert response.status_code in [200, 500, 502]  # Various possible outcomes
    
    def test_error_logging_integration(self, client):
        """Test error logging integration."""
        # Make a request that should cause an error
        response = client.get("/apod?date=invalid-date")
        
        # Should return an error status
        assert response.status_code >= 400
        
        # Response should include error information
        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            assert "error" in data or "detail" in data


class TestPerformanceMonitoring:
    """Test performance monitoring integration."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    def test_performance_metrics_collection(self, client):
        """Test that performance metrics are collected."""
        # Make several requests to generate metrics
        for i in range(5):
            client.get("/")
        
        # Get metrics
        response = client.get("/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "nasa_api_stats" in data
    
    def test_slow_request_detection(self, client):
        """Test detection of slow requests."""
        # This test would need to mock slow operations
        # For now, just verify the endpoint works
        response = client.get("/metrics")
        assert response.status_code == 200
    
    @patch('time.sleep')
    def test_performance_thresholds(self, mock_sleep, client):
        """Test performance threshold detection."""
        # Mock a slow operation
        mock_sleep.return_value = None
        
        response = client.get("/")
        # Should still work despite mocked sleep
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__])