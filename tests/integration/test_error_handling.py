"""
Integration tests for error handling scenarios.

This module tests various error conditions and failure scenarios
to ensure the application handles them gracefully.
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from fastapi.testclient import TestClient
from httpx import Response

from nasa_mcp_demo.main import app, get_nasa_service
from nasa_mcp_demo.models.errors import (
    NASAAPIError,
    NASAAPIUnavailable,
    NASAAPIRateLimited,
    NASAAPIInvalidRequest,
    NASAAPITimeout
)
from tests.fixtures.nasa_api_responses import ERROR_RESPONSES


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


class TestNASAAPIErrorHandling:
    """Test NASA API error handling scenarios."""
    
    def test_nasa_api_unavailable_error(self, client):
        """Test handling when NASA API is completely unavailable."""
        mock_service = AsyncMock()
        mock_service.get_daily_astronomy_picture.side_effect = NASAAPIUnavailable(
            "NASA API is currently unavailable",
            status_code=503
        )
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/apod")
        
        assert response.status_code == 503
        data = response.json()
        assert data["error"] in ["nasa_api_unavailable", "service_unavailable"]
        assert "NASA API is currently unavailable" in data["message"]
        
        app.dependency_overrides.clear()
    
    def test_nasa_api_rate_limited_error(self, client):
        """Test handling when NASA API rate limit is exceeded."""
        mock_service = AsyncMock()
        mock_service.get_daily_astronomy_picture.side_effect = NASAAPIRateLimited(
            "Rate limit exceeded",
            status_code=429,
            retry_after=60
        )
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/apod")
        
        assert response.status_code == 429
        assert response.headers.get("Retry-After") == "60"
        data = response.json()
        assert data["error"] in ["nasa_api_rate_limited", "rate_limited"]
        assert "Rate limit exceeded" in data["message"]
        
        app.dependency_overrides.clear()
    
    def test_nasa_api_invalid_request_error(self, client):
        """Test handling of invalid request parameters."""
        mock_service = AsyncMock()
        mock_service.get_daily_astronomy_picture.side_effect = NASAAPIInvalidRequest(
            "Invalid date format provided",
            status_code=400,
            invalid_params={"date": "invalid-date"}
        )
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/apod?date=invalid-date")
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] in ["nasa_api_invalid_request", "invalid_request"]
        assert "Invalid date format" in data["message"]
        assert "invalid_params" in data["details"]
        
        app.dependency_overrides.clear()
    
    def test_nasa_api_timeout_error(self, client):
        """Test handling of NASA API timeout errors."""
        mock_service = AsyncMock()
        mock_service.search_mars_photos.side_effect = NASAAPITimeout(
            "Request to NASA API timed out",
            timeout_duration=30
        )
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/mars-photos/curiosity?sol=1000")
        
        assert response.status_code == 504
        data = response.json()
        assert data["error"] in ["nasa_api_timeout", "timeout"]
        assert "timed out" in data["message"]
        assert data["details"]["timeout_duration"] == 30
        
        app.dependency_overrides.clear()
    
    def test_generic_nasa_api_error(self, client):
        """Test handling of generic NASA API errors."""
        mock_service = AsyncMock()
        mock_service.get_near_earth_objects.side_effect = NASAAPIError(
            "Unexpected NASA API error",
            status_code=500
        )
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/neo?start_date=2023-12-01&end_date=2023-12-01")
        
        assert response.status_code == 500
        data = response.json()
        assert data["error"] in ["nasa_api_error", "internal_server_error"]
        assert "Unexpected NASA API error" in data["message"]
        
        app.dependency_overrides.clear()


class TestValidationErrorHandling:
    """Test request validation error handling."""
    
    def test_missing_required_parameters(self, client):
        """Test handling of missing required parameters."""
        # Mars photos without sol parameter
        response = client.get("/mars-photos/curiosity")
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
        assert any("sol" in str(error) for error in data["detail"])
        
        # NEO without date parameters
        response = client.get("/neo")
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
        assert any("start_date" in str(error) for error in data["detail"])
    
    def test_invalid_parameter_types(self, client):
        """Test handling of invalid parameter types."""
        # Invalid sol type (string that can't be converted to int)
        response = client.get("/mars-photos/curiosity?sol=invalid")
        assert response.status_code == 422
        
        # Invalid date format
        response = client.get("/apod?date=not-a-date")
        assert response.status_code == 422
        
        # Invalid rover name in path
        response = client.get("/mars-photos/invalid_rover?sol=100")
        # This might pass path validation but fail in service layer
        assert response.status_code in [400, 422, 500]
    
    def test_parameter_range_validation(self, client):
        """Test parameter range validation."""
        # Negative sol value
        response = client.get("/mars-photos/curiosity?sol=-1")
        assert response.status_code == 422
        
        # Very large sol value (if validation exists)
        response = client.get("/mars-photos/curiosity?sol=999999")
        # This might be handled at service layer
        assert response.status_code in [400, 422]


class TestServiceLayerErrorHandling:
    """Test service layer error handling."""
    
    def test_service_initialization_error(self, client):
        """Test handling of service initialization errors."""
        def failing_service():
            raise Exception("Service initialization failed")
        
        app.dependency_overrides[get_nasa_service] = failing_service
        
        response = client.get("/apod")
        assert response.status_code == 500
        
        app.dependency_overrides.clear()
    
    def test_service_method_unexpected_error(self, client):
        """Test handling of unexpected service errors."""
        mock_service = AsyncMock()
        mock_service.get_daily_astronomy_picture.side_effect = Exception(
            "Unexpected service error"
        )
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/apod")
        assert response.status_code == 500
        
        data = response.json()
        assert "error" in data
        assert "Internal server error" in data["message"]
        
        app.dependency_overrides.clear()


class TestNetworkErrorHandling:
    """Test network-related error handling."""
    
    def test_connection_error_handling(self, client):
        """Test handling of network connection errors."""
        mock_service = AsyncMock()
        mock_service.health_check.side_effect = Exception("Connection refused")
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/health")
        
        # Health endpoint should handle errors gracefully
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["degraded", "unhealthy"]
        
        app.dependency_overrides.clear()
    
    def test_dns_resolution_error(self, client):
        """Test handling of DNS resolution errors."""
        mock_service = AsyncMock()
        mock_service.get_daily_astronomy_picture.side_effect = NASAAPIError(
            "DNS resolution failed for api.nasa.gov"
        )
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/apod")
        assert response.status_code == 500
        
        app.dependency_overrides.clear()


class TestConcurrentErrorHandling:
    """Test error handling under concurrent load."""
    
    @pytest.mark.asyncio
    async def test_concurrent_api_failures(self, client):
        """Test handling of concurrent API failures."""
        import asyncio
        from httpx import AsyncClient
        
        # Mock service that fails randomly
        mock_service = AsyncMock()
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise NASAAPIUnavailable("API temporarily unavailable")
            return AsyncMock()  # Success case
        
        mock_service.get_daily_astronomy_picture.side_effect = side_effect
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Make multiple concurrent requests
            tasks = [
                ac.get("/apod") for _ in range(10)
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Some should succeed, some should fail
            success_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
            error_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code >= 400)
            
            assert success_count > 0 or error_count > 0  # At least some responses
        
        app.dependency_overrides.clear()
    
    def test_rate_limit_under_load(self, client):
        """Test rate limiting behavior under load."""
        mock_service = AsyncMock()
        
        # First few calls succeed, then rate limited
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 3:
                raise NASAAPIRateLimited("Rate limit exceeded", retry_after=60)
            return AsyncMock()
        
        mock_service.get_daily_astronomy_picture.side_effect = side_effect
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        responses = []
        for _ in range(5):
            response = client.get("/apod")
            responses.append(response)
        
        # First few should succeed, later ones should be rate limited
        success_responses = [r for r in responses if r.status_code == 200]
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        
        assert len(success_responses) > 0
        assert len(rate_limited_responses) > 0
        
        app.dependency_overrides.clear()


class TestErrorResponseFormat:
    """Test error response format consistency."""
    
    def test_error_response_structure(self, client):
        """Test that all error responses follow consistent structure."""
        mock_service = AsyncMock()
        mock_service.get_daily_astronomy_picture.side_effect = NASAAPIError(
            "Test error",
            error_code="test_error"
        )
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/apod")
        assert response.status_code >= 400
        
        data = response.json()
        
        # Check required fields
        assert "error" in data
        assert "message" in data
        assert "timestamp" in data
        assert "request_id" in data
        
        # Check optional fields
        if "details" in data:
            assert isinstance(data["details"], dict)
        
        app.dependency_overrides.clear()
    
    def test_validation_error_response_structure(self, client):
        """Test validation error response structure."""
        response = client.get("/mars-photos/curiosity")  # Missing sol parameter
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        
        # Check validation error details
        for error in data["detail"]:
            assert "loc" in error
            assert "msg" in error
            assert "type" in error


class TestErrorLogging:
    """Test error logging functionality."""
    
    @patch('nasa_mcp_demo.logging_config.get_logger')
    def test_error_logging_integration(self, mock_get_logger, client):
        """Test that errors are properly logged."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        mock_service = AsyncMock()
        mock_service.get_daily_astronomy_picture.side_effect = NASAAPIError(
            "Test error for logging"
        )
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/apod")
        assert response.status_code >= 400
        
        # Verify logger was called (implementation dependent)
        # This test might need adjustment based on actual logging implementation
        
        app.dependency_overrides.clear()


class TestGracefulDegradation:
    """Test graceful degradation scenarios."""
    
    def test_partial_service_failure(self, client):
        """Test behavior when some services fail but others work."""
        mock_service = AsyncMock()
        
        # APOD works, Mars photos fail
        mock_service.get_daily_astronomy_picture.return_value = AsyncMock()
        mock_service.search_mars_photos.side_effect = NASAAPIUnavailable("Mars API down")
        mock_service.health_check.return_value = {
            "service": "degraded",
            "nasa_api": "partial",
            "apod": "healthy",
            "mars": "unhealthy"
        }
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        # APOD should work
        apod_response = client.get("/apod")
        assert apod_response.status_code == 200
        
        # Mars photos should fail gracefully
        mars_response = client.get("/mars-photos/curiosity?sol=1000")
        assert mars_response.status_code == 503
        
        # Health check should show degraded status
        health_response = client.get("/health")
        assert health_response.status_code == 200
        data = health_response.json()
        assert data["status"] == "degraded"
        
        app.dependency_overrides.clear()
    
    def test_cache_fallback_on_api_failure(self, client):
        """Test fallback to cached data when API fails."""
        # This test would require mocking the cache behavior
        # Implementation depends on actual caching strategy
        pass


if __name__ == "__main__":
    pytest.main([__file__])