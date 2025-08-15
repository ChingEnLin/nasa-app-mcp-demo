"""
Integration tests for NASA service layer.

This module contains integration tests that verify the NASA service layer
works correctly with the NASA client and handles real-world scenarios.
"""

import pytest
from unittest.mock import AsyncMock, patch

from nasa_mcp_demo.services.nasa_service import NASAService
from nasa_mcp_demo.clients.nasa_client import NASAClient
from nasa_mcp_demo.models.config import AppConfig, NASAConfig, CacheConfig
from nasa_mcp_demo.models.errors import NASAAPIError, NASAAPIInvalidRequest


@pytest.fixture
def integration_config():
    """Create configuration for integration testing."""
    return AppConfig(
        nasa=NASAConfig(
            api_key="DEMO_KEY",
            timeout=10,
            max_retries=1
        ),
        cache=CacheConfig(
            enable_caching=True,
            apod_cache_ttl=60,
            mars_photos_cache_ttl=60,
            neo_cache_ttl=60,
            max_cache_size=10
        )
    )


class TestNASAServiceIntegration:
    """Integration tests for NASA service with real client."""
    
    @pytest.mark.asyncio
    async def test_service_with_real_client_creation(self, integration_config):
        """Test service creation with real NASA client."""
        service = NASAService(integration_config)
        
        # Service should create client on demand
        assert service.nasa_client is None
        
        client = await service.get_nasa_client()
        assert isinstance(client, NASAClient)
        assert service.nasa_client is client
        
        # Subsequent calls should return same client
        client2 = await service.get_nasa_client()
        assert client2 is client
        
        # Clean up
        await client.close()
    
    @pytest.mark.asyncio
    async def test_service_error_handling_with_client(self, integration_config):
        """Test service error handling with client errors."""
        service = NASAService(integration_config)
        
        # Mock the client to raise an error
        mock_client = AsyncMock()
        mock_client.get_apod.side_effect = NASAAPIError("Test API error")
        service.nasa_client = mock_client
        
        with pytest.raises(NASAAPIError) as exc_info:
            await service.get_daily_astronomy_picture("2023-12-01")
        
        assert "Test API error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_service_caching_behavior(self, integration_config):
        """Test service caching behavior with multiple requests."""
        service = NASAService(integration_config)
        
        # Mock successful client response
        mock_client = AsyncMock()
        from nasa_mcp_demo.models.nasa_responses import APODResponse
        
        mock_apod = APODResponse(
            date="2023-12-01",
            title="Test APOD",
            explanation="Test explanation.",
            url="https://example.com/image.jpg",
            media_type="image"
        )
        mock_client.get_apod.return_value = mock_apod
        service.nasa_client = mock_client
        
        # First request should call client
        result1 = await service.get_daily_astronomy_picture("2023-12-01")
        assert mock_client.get_apod.call_count == 1
        
        # Second request should use cache
        result2 = await service.get_daily_astronomy_picture("2023-12-01")
        assert mock_client.get_apod.call_count == 1  # Still 1, not called again
        
        # Results should be equivalent
        assert result1.date == result2.date
        assert result1.title == result2.title
    
    @pytest.mark.asyncio
    async def test_service_validation_integration(self, integration_config):
        """Test service validation with various input scenarios."""
        service = NASAService(integration_config)
        
        # Test various invalid inputs
        from datetime import date, timedelta
        future_date = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        invalid_inputs = [
            ("get_daily_astronomy_picture", [future_date]),  # Future date
            ("get_daily_astronomy_picture", ["1990-01-01"]),  # Before APOD started
            ("get_daily_astronomy_picture", ["invalid-date"]),  # Invalid format
            ("search_mars_photos", ["invalid_rover", 100]),  # Invalid rover
            ("search_mars_photos", ["curiosity", -1]),  # Invalid sol
            ("search_mars_photos", ["curiosity", 100, "INVALID_CAM"]),  # Invalid camera
            ("get_near_earth_objects", ["2023-12-01", "2023-11-01"]),  # End before start
            ("get_near_earth_objects", ["2023-12-01", "2023-12-10"]),  # Range too large
        ]
        
        for method_name, args in invalid_inputs:
            method = getattr(service, method_name)
            with pytest.raises(NASAAPIInvalidRequest):
                await method(*args)
    
    @pytest.mark.asyncio
    async def test_service_health_check_integration(self, integration_config):
        """Test service health check integration."""
        service = NASAService(integration_config)
        
        # Mock client health check
        mock_client = AsyncMock()
        mock_client.health_check.return_value = True
        service.nasa_client = mock_client
        
        health_status = await service.health_check()
        
        assert health_status["service"] == "healthy"
        assert health_status["nasa_api"] == "healthy"
        assert health_status["cache"] == "enabled"
        assert "timestamp" in health_status
        assert "cache_stats" in health_status
        
        # Test with API failure
        mock_client.health_check.side_effect = Exception("Connection failed")
        health_status = await service.health_check()
        
        assert health_status["service"] == "healthy"
        assert health_status["nasa_api"] == "unhealthy"
        assert "nasa_api_error" in health_status
    
    @pytest.mark.asyncio
    async def test_service_concurrent_requests(self, integration_config):
        """Test service handling of concurrent requests."""
        import asyncio
        
        service = NASAService(integration_config)
        
        # Mock client with delay to simulate real API
        mock_client = AsyncMock()
        from nasa_mcp_demo.models.nasa_responses import APODResponse
        
        async def mock_get_apod(date=None):
            await asyncio.sleep(0.01)  # Small delay
            return APODResponse(
                date=date or "2023-12-01",
                title=f"APOD for {date}",
                explanation="Test explanation.",
                url="https://example.com/image.jpg",
                media_type="image"
            )
        
        mock_client.get_apod.side_effect = mock_get_apod
        service.nasa_client = mock_client
        
        # Make concurrent requests for different dates
        tasks = [
            service.get_daily_astronomy_picture("2023-12-01"),
            service.get_daily_astronomy_picture("2023-12-02"),
            service.get_daily_astronomy_picture("2023-12-03"),
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All requests should succeed
        assert len(results) == 3
        assert all(result.title.startswith("APOD for") for result in results)
        
        # Each should have different dates
        dates = [result.date for result in results]
        assert len(set(dates)) == 3  # All unique dates
    
    @pytest.mark.asyncio
    async def test_service_cache_expiration_behavior(self, integration_config):
        """Test service cache expiration behavior."""
        # Set very short cache TTL for testing
        integration_config.cache.apod_cache_ttl = 1  # 1 second
        service = NASAService(integration_config)
        
        # Mock client
        mock_client = AsyncMock()
        from nasa_mcp_demo.models.nasa_responses import APODResponse
        
        mock_apod = APODResponse(
            date="2023-12-01",
            title="Test APOD",
            explanation="Test explanation.",
            url="https://example.com/image.jpg",
            media_type="image"
        )
        mock_client.get_apod.return_value = mock_apod
        service.nasa_client = mock_client
        
        # First request
        await service.get_daily_astronomy_picture("2023-12-01")
        assert mock_client.get_apod.call_count == 1
        
        # Wait for cache to expire
        import asyncio
        await asyncio.sleep(1.1)
        
        # Second request should call client again due to expiration
        await service.get_daily_astronomy_picture("2023-12-01")
        assert mock_client.get_apod.call_count == 2
    
    @pytest.mark.asyncio
    async def test_service_data_enrichment_integration(self, integration_config):
        """Test service data enrichment with realistic data."""
        service = NASAService(integration_config)
        
        # Mock client with realistic responses
        mock_client = AsyncMock()
        service.nasa_client = mock_client
        
        # Test APOD enrichment
        from nasa_mcp_demo.models.nasa_responses import APODResponse
        mock_apod = APODResponse(
            date="2023-12-01",
            title="Amazing Galaxy",
            explanation="This beautiful galaxy contains billions of stars and spans thousands of light years.",
            url="https://example.com/galaxy.jpg",
            media_type="image",
            hdurl="https://example.com/galaxy_hd.jpg"
        )
        mock_client.get_apod.return_value = mock_apod
        
        result = await service.get_daily_astronomy_picture("2023-12-01")
        
        # Check enrichments
        assert result.is_image is True
        assert result.has_hd_version is True
        assert result.word_count > 0
        assert result.is_recent is False  # 2023 date
        
        # Test Mars photos enrichment
        from nasa_mcp_demo.models.nasa_responses import MarsRoverResponse, MarsPhoto
        mock_photos = [
            MarsPhoto(
                id=1,
                img_src="https://example.com/mars1.jpg",
                earth_date="2023-12-01",
                rover_name="curiosity",
                camera_name="MAST",
                camera_full_name="Mast Camera"
            ),
            MarsPhoto(
                id=2,
                img_src="https://example.com/mars2.jpg",
                earth_date="2023-12-01",
                rover_name="curiosity",
                camera_name="FHAZ",
                camera_full_name="Front Hazard Avoidance Camera"
            )
        ]
        mock_mars_response = MarsRoverResponse(
            photos=mock_photos,
            rover="curiosity",
            sol=100,
            total_photos=2
        )
        mock_client.get_mars_rover_photos.return_value = mock_mars_response
        
        mars_result = await service.search_mars_photos("curiosity", 100)
        
        # Check enrichments
        assert mars_result.has_photos is True
        assert len(mars_result.cameras_used) == 2
        assert "MAST" in mars_result.cameras_used
        assert "FHAZ" in mars_result.cameras_used
        assert mars_result.camera_summary["MAST"] == 1
        assert mars_result.camera_summary["FHAZ"] == 1
        
        # Check photo-level enrichments
        mast_photo = next(p for p in mars_result.photos if p["camera_name"] == "MAST")
        assert mast_photo["is_color_camera"] is True
        assert mast_photo["camera_type"] == "Mast Camera"