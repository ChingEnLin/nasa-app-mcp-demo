"""
Unit tests for NASA API client.

This module contains comprehensive tests for the NASA API client including
normal operations, error handling, retry logic, and rate limiting.
"""

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

import httpx
import pytest
from httpx import Response

from nasa_mcp_demo.clients.nasa_client import NASAClient, RateLimiter
from nasa_mcp_demo.models.config import NASAConfig
from nasa_mcp_demo.models.errors import (
    NASAAPIError,
    NASAAPIUnavailable,
    NASAAPIRateLimited,
    NASAAPIInvalidRequest,
    NASAAPITimeout,
)
from nasa_mcp_demo.models.nasa_responses import APODResponse, MarsRoverResponse, NEOResponse


class TestRateLimiter:
    """Test cases for RateLimiter class."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_within_limit(self):
        """Test that rate limiter allows requests within the limit."""
        limiter = RateLimiter(max_requests=5, time_window=60)
        
        # Should allow 5 requests without blocking
        for _ in range(5):
            await limiter.acquire()
        
        # Check that requests were recorded
        assert len(limiter.requests) == 5
    
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_when_limit_exceeded(self):
        """Test that rate limiter blocks when limit is exceeded."""
        limiter = RateLimiter(max_requests=2, time_window=1)
        
        # Make 2 requests (should be allowed)
        await limiter.acquire()
        await limiter.acquire()
        
        # Manually add old requests to simulate time passing
        old_time = datetime.now() - timedelta(seconds=2)
        limiter.requests = [old_time, old_time]
        
        # Third request should now be allowed since old requests are cleaned up
        start_time = datetime.now()
        await limiter.acquire()
        end_time = datetime.now()
        
        # Should not have waited long since old requests were cleaned up
        assert (end_time - start_time).total_seconds() < 0.1
    
    @pytest.mark.asyncio
    async def test_rate_limiter_cleans_old_requests(self):
        """Test that rate limiter removes old requests from tracking."""
        limiter = RateLimiter(max_requests=5, time_window=1)
        
        # Add some old requests manually
        old_time = datetime.now() - timedelta(seconds=2)
        limiter.requests = [old_time, old_time]
        
        # Make a new request
        await limiter.acquire()
        
        # Old requests should be cleaned up
        assert len(limiter.requests) == 1
        assert all(req > old_time for req in limiter.requests)


class TestNASAClient:
    """Test cases for NASAClient class."""
    
    @pytest.fixture
    def nasa_config(self):
        """Create a test NASA configuration."""
        return NASAConfig(
            api_key="test_key",
            base_url="https://api.nasa.gov",
            timeout=30,
            max_retries=3,
            rate_limit_per_hour=1000,
            retry_backoff_factor=1.0
        )
    
    @pytest.fixture
    def nasa_client(self, nasa_config):
        """Create a NASA client for testing."""
        return NASAClient(nasa_config)
    
    def create_mock_response(self, status_code: int, json_data: Dict[str, Any]) -> Response:
        """Create a mock HTTP response."""
        response = Mock(spec=Response)
        response.status_code = status_code
        response.json.return_value = json_data
        response.text = json.dumps(json_data)
        response.headers = {}
        return response
    
    @pytest.mark.asyncio
    async def test_client_context_manager(self, nasa_client):
        """Test that client works as async context manager."""
        async with nasa_client as client:
            assert client._client is not None
            assert not client._client.is_closed
        
        # Client should be closed after exiting context
        assert nasa_client._client.is_closed
    
    @pytest.mark.asyncio
    async def test_successful_apod_request(self, nasa_client):
        """Test successful APOD API request."""
        mock_response_data = {
            "date": "2023-12-01",
            "title": "Test APOD",
            "explanation": "Test explanation",
            "url": "https://example.com/image.jpg",
            "media_type": "image",
            "copyright": "Test Copyright",
            "hdurl": "https://example.com/hd_image.jpg"
        }
        
        mock_response = self.create_mock_response(200, mock_response_data)
        
        with patch.object(nasa_client, '_ensure_client') as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_ensure_client.return_value = mock_client
            
            result = await nasa_client.get_apod("2023-12-01")
            
            assert isinstance(result, APODResponse)
            assert result.date == "2023-12-01"
            assert result.title == "Test APOD"
            assert result.media_type == "image"
            
            # Verify the request was made with correct parameters
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert "api_key" in call_args[1]["params"]
            assert call_args[1]["params"]["date"] == "2023-12-01"
    
    @pytest.mark.asyncio
    async def test_successful_mars_rover_request(self, nasa_client):
        """Test successful Mars rover photos API request."""
        mock_response_data = {
            "photos": [
                {
                    "id": 123,
                    "img_src": "https://example.com/mars_photo.jpg",
                    "earth_date": "2023-12-01",
                    "rover": {"name": "Curiosity"},
                    "camera": {"name": "MAST", "full_name": "Mast Camera"}
                }
            ]
        }
        
        mock_response = self.create_mock_response(200, mock_response_data)
        
        with patch.object(nasa_client, '_ensure_client') as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_ensure_client.return_value = mock_client
            
            result = await nasa_client.get_mars_rover_photos("curiosity", 1000, "MAST")
            
            assert isinstance(result, MarsRoverResponse)
            assert result.rover == "curiosity"
            assert result.sol == 1000
            assert result.total_photos == 1
            assert len(result.photos) == 1
            assert result.photos[0].id == 123
            assert result.photos[0].rover_name == "curiosity"
    
    @pytest.mark.asyncio
    async def test_successful_neo_request(self, nasa_client):
        """Test successful NEO API request."""
        mock_response_data = {
            "near_earth_objects": {
                "2023-12-01": [
                    {
                        "id": "123456",
                        "name": "Test Asteroid",
                        "estimated_diameter": {
                            "kilometers": {
                                "estimated_diameter_min": 0.1,
                                "estimated_diameter_max": 0.2
                            }
                        },
                        "is_potentially_hazardous_asteroid": False,
                        "close_approach_data": [
                            {
                                "close_approach_date": "2023-12-01",
                                "miss_distance": {"kilometers": "1000000"},
                                "relative_velocity": {"kilometers_per_hour": "50000"}
                            }
                        ]
                    }
                ]
            },
            "element_count": 1
        }
        
        mock_response = self.create_mock_response(200, mock_response_data)
        
        with patch.object(nasa_client, '_ensure_client') as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_ensure_client.return_value = mock_client
            
            result = await nasa_client.get_neo_data("2023-12-01", "2023-12-01")
            
            assert isinstance(result, NEOResponse)
            assert result.element_count == 1
            assert "2023-12-01" in result.near_earth_objects
            assert len(result.near_earth_objects["2023-12-01"]) == 1
            
            neo = result.near_earth_objects["2023-12-01"][0]
            assert neo.id == "123456"
            assert neo.name == "Test Asteroid"
            assert not neo.is_potentially_hazardous
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, nasa_client):
        """Test handling of rate limit errors."""
        mock_response = self.create_mock_response(429, {"error": {"message": "Rate limit exceeded"}})
        mock_response.headers = {"Retry-After": "60"}
        
        with patch.object(nasa_client, '_ensure_client') as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_ensure_client.return_value = mock_client
            
            with pytest.raises(NASAAPIRateLimited) as exc_info:
                await nasa_client.get_apod()
            
            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after == 60
    
    @pytest.mark.asyncio
    async def test_invalid_request_error_handling(self, nasa_client):
        """Test handling of invalid request errors."""
        mock_response = self.create_mock_response(400, {"error": {"message": "Invalid date format"}})
        
        with patch.object(nasa_client, '_ensure_client') as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_ensure_client.return_value = mock_client
            
            with pytest.raises(NASAAPIInvalidRequest) as exc_info:
                await nasa_client.get_apod("invalid-date")
            
            assert exc_info.value.status_code == 400
            assert "Invalid date format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_forbidden_error_handling(self, nasa_client):
        """Test handling of forbidden errors (API key issues)."""
        mock_response = self.create_mock_response(403, {"error": {"message": "Invalid API key"}})
        
        with patch.object(nasa_client, '_ensure_client') as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_ensure_client.return_value = mock_client
            
            with pytest.raises(NASAAPIInvalidRequest) as exc_info:
                await nasa_client.get_apod()
            
            assert exc_info.value.status_code == 403
            assert "API key invalid" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_server_error_retry_logic(self, nasa_client):
        """Test retry logic for server errors."""
        # First two requests fail with 500, third succeeds
        error_response = self.create_mock_response(500, {"error": {"message": "Internal server error"}})
        success_response = self.create_mock_response(200, {
            "date": "2023-12-01",
            "title": "Test APOD",
            "explanation": "Test explanation",
            "url": "https://example.com/image.jpg",
            "media_type": "image"
        })
        
        with patch.object(nasa_client, '_ensure_client') as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [error_response, error_response, success_response]
            mock_ensure_client.return_value = mock_client
            
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                result = await nasa_client.get_apod()
                
                assert isinstance(result, APODResponse)
                assert mock_client.get.call_count == 3
                assert mock_sleep.call_count == 2  # Two retries
    
    @pytest.mark.asyncio
    async def test_server_error_max_retries_exceeded(self, nasa_client):
        """Test that server errors raise exception after max retries."""
        error_response = self.create_mock_response(500, {"error": {"message": "Internal server error"}})
        
        with patch.object(nasa_client, '_ensure_client') as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.get.return_value = error_response
            mock_ensure_client.return_value = mock_client
            
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(NASAAPIUnavailable) as exc_info:
                    await nasa_client.get_apod()
                
                assert exc_info.value.status_code == 500
                assert mock_client.get.call_count == 4  # Initial + 3 retries
    
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, nasa_client):
        """Test handling of timeout errors."""
        with patch.object(nasa_client, '_ensure_client') as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
            mock_ensure_client.return_value = mock_client
            
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(NASAAPITimeout) as exc_info:
                    await nasa_client.get_apod()
                
                assert exc_info.value.timeout_duration == 30
                assert mock_client.get.call_count == 4  # Initial + 3 retries
    
    @pytest.mark.asyncio
    async def test_timeout_retry_logic(self, nasa_client):
        """Test retry logic for timeout errors."""
        success_response = self.create_mock_response(200, {
            "date": "2023-12-01",
            "title": "Test APOD",
            "explanation": "Test explanation",
            "url": "https://example.com/image.jpg",
            "media_type": "image"
        })
        
        with patch.object(nasa_client, '_ensure_client') as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [
                httpx.TimeoutException("Timeout"),
                success_response
            ]
            mock_ensure_client.return_value = mock_client
            
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                result = await nasa_client.get_apod()
                
                assert isinstance(result, APODResponse)
                assert mock_client.get.call_count == 2
                assert mock_sleep.call_count == 1
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, nasa_client):
        """Test successful health check."""
        mock_response = self.create_mock_response(200, {
            "date": "2023-12-01",
            "title": "Test APOD",
            "explanation": "Test explanation",
            "url": "https://example.com/image.jpg",
            "media_type": "image"
        })
        
        with patch.object(nasa_client, '_ensure_client') as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_ensure_client.return_value = mock_client
            
            result = await nasa_client.health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, nasa_client):
        """Test health check failure."""
        with patch.object(nasa_client, '_ensure_client') as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.get.side_effect = NASAAPIError("API unavailable")
            mock_ensure_client.return_value = mock_client
            
            result = await nasa_client.health_check()
            assert result is False
    
    def test_calculate_backoff_time(self, nasa_client):
        """Test exponential backoff calculation."""
        # Test with default backoff factor of 1.0
        assert nasa_client._calculate_backoff_time(0) == 1.0
        assert nasa_client._calculate_backoff_time(1) == 2.0
        assert nasa_client._calculate_backoff_time(2) == 4.0
        assert nasa_client._calculate_backoff_time(3) == 8.0
        
        # Test that it caps at 60 seconds
        assert nasa_client._calculate_backoff_time(10) == 60.0
    
    def test_safe_json_parse_success(self, nasa_client):
        """Test successful JSON parsing."""
        mock_response = Mock()
        mock_response.json.return_value = {"key": "value"}
        
        result = nasa_client._safe_json_parse(mock_response)
        assert result == {"key": "value"}
    
    def test_safe_json_parse_failure(self, nasa_client):
        """Test JSON parsing failure handling."""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Invalid response"
        
        result = nasa_client._safe_json_parse(mock_response)
        assert result == {"error": {"message": "Invalid response"}}
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, nasa_client):
        """Test that rate limiting is applied to requests."""
        # Mock the rate limiter to avoid actual delays in tests
        mock_rate_limiter = AsyncMock()
        nasa_client.rate_limiter = mock_rate_limiter
        
        mock_response = self.create_mock_response(200, {
            "date": "2023-12-01",
            "title": "Test APOD",
            "explanation": "Test explanation",
            "url": "https://example.com/image.jpg",
            "media_type": "image"
        })
        
        with patch.object(nasa_client, '_ensure_client') as mock_ensure_client:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_ensure_client.return_value = mock_client
            
            # Make two requests
            await nasa_client.get_apod()
            await nasa_client.get_apod()
            
            # Verify rate limiter was called for each request
            assert mock_rate_limiter.acquire.call_count == 2
            assert mock_client.get.call_count == 2