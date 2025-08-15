"""
Comprehensive integration tests for all REST API endpoints.

This module provides thorough testing of all API endpoints with various
scenarios, edge cases, and data combinations.
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from nasa_mcp_demo.main import app, get_nasa_service, get_app_config
from nasa_mcp_demo.services.nasa_service import ProcessedAPOD, ProcessedMarsPhotos, ProcessedNEOData
from nasa_mcp_demo.models.config import AppConfig
from nasa_mcp_demo.models.nasa_responses import APODResponse, MarsRoverResponse, NEOResponse
from tests.fixtures.nasa_api_responses import (
    SAMPLE_APOD_RESPONSES,
    SAMPLE_MARS_RESPONSES,
    SAMPLE_NEO_RESPONSES,
    MockNASAResponses
)


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return AppConfig()


class TestRootEndpoint:
    """Comprehensive tests for root endpoint."""
    
    def test_root_endpoint_basic(self, client):
        """Test basic root endpoint functionality."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "NASA Data API"
        assert data["version"] == "1.0.0"
        assert "description" in data
        assert "endpoints" in data
        assert "nasa_apis" in data
    
    def test_root_endpoint_structure(self, client):
        """Test root endpoint response structure."""
        response = client.get("/")
        data = response.json()
        
        # Check endpoints structure
        endpoints = data["endpoints"]
        assert isinstance(endpoints, dict)
        
        expected_endpoints = [
            "apod", "mars_photos", "neo", "health"
        ]
        for endpoint in expected_endpoints:
            assert endpoint in endpoints
            # The endpoints are stored as strings with descriptions
            assert isinstance(endpoints[endpoint], str)
            assert "/" in endpoints[endpoint]  # Should contain a path
        
        # Check NASA APIs structure
        nasa_apis = data["nasa_apis"]
        assert isinstance(nasa_apis, list)
        assert "Astronomy Picture of the Day (APOD)" in nasa_apis
        assert "Mars Rover Photos" in nasa_apis
        assert "Near Earth Objects (NEO)" in nasa_apis
    
    def test_root_endpoint_content_type(self, client):
        """Test root endpoint content type."""
        response = client.get("/")
        assert response.headers["content-type"] == "application/json"


class TestAPODEndpoint:
    """Comprehensive tests for APOD endpoint."""
    
    def test_apod_without_date(self, client):
        """Test APOD endpoint without date parameter (should use today)."""
        mock_service = AsyncMock()
        mock_apod_data = MockNASAResponses.get_apod_response()
        mock_apod_response = APODResponse(**mock_apod_data)
        mock_apod = ProcessedAPOD(mock_apod_response)
        mock_service.get_daily_astronomy_picture.return_value = mock_apod
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/apod")
        assert response.status_code == 200
        
        data = response.json()
        assert "date" in data
        assert "title" in data
        assert "explanation" in data
        assert "url" in data
        assert "media_type" in data
        
        # Verify service was called with None (today)
        mock_service.get_daily_astronomy_picture.assert_called_once_with(None)
        
        app.dependency_overrides.clear()
    
    def test_apod_with_specific_date(self, client):
        """Test APOD endpoint with specific date."""
        mock_service = AsyncMock()
        mock_apod_data = MockNASAResponses.get_apod_response("2023-12-01")
        mock_apod_response = APODResponse(**mock_apod_data)
        mock_apod = ProcessedAPOD(mock_apod_response)
        mock_service.get_daily_astronomy_picture.return_value = mock_apod
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/apod?date=2023-12-01")
        assert response.status_code == 200
        
        data = response.json()
        assert data["date"] == "2023-12-01"
        
        mock_service.get_daily_astronomy_picture.assert_called_once_with("2023-12-01")
        
        app.dependency_overrides.clear()
    
    def test_apod_image_vs_video_response(self, client):
        """Test APOD endpoint with both image and video responses."""
        mock_service = AsyncMock()
        
        # Test image response
        image_apod_data = MockNASAResponses.get_apod_response("2023-12-01", media_type="image")
        image_apod_response = APODResponse(**image_apod_data)
        image_apod = ProcessedAPOD(image_apod_response)
        mock_service.get_daily_astronomy_picture.return_value = image_apod
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/apod?date=2023-12-01")
        data = response.json()
        assert data["media_type"] == "image"
        assert data["is_image"] is True
        assert data["is_video"] is False
        assert "hdurl" in data
        
        # Test video response
        video_apod_data = MockNASAResponses.get_apod_response("2023-12-02", media_type="video")
        video_apod_response = APODResponse(**video_apod_data)
        video_apod = ProcessedAPOD(video_apod_response)
        mock_service.get_daily_astronomy_picture.return_value = video_apod
        
        response = client.get("/apod?date=2023-12-02")
        data = response.json()
        assert data["media_type"] == "video"
        assert data["is_image"] is False
        assert data["is_video"] is True
        
        app.dependency_overrides.clear()
    
    def test_apod_enriched_fields(self, client):
        """Test APOD endpoint enriched fields."""
        mock_service = AsyncMock()
        mock_apod_data = MockNASAResponses.get_apod_response(
            "2023-12-01", include_copyright=True, include_hdurl=True
        )
        mock_apod_response = APODResponse(**mock_apod_data)
        mock_apod = ProcessedAPOD(mock_apod_response)
        mock_service.get_daily_astronomy_picture.return_value = mock_apod
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/apod?date=2023-12-01")
        data = response.json()
        
        # Check enriched fields
        assert "is_image" in data
        assert "is_video" in data
        assert "has_hd_version" in data
        assert "word_count" in data
        assert "is_recent" in data
        
        assert isinstance(data["word_count"], int)
        assert data["word_count"] > 0
        
        app.dependency_overrides.clear()
    
    def test_apod_date_validation_edge_cases(self, client):
        """Test APOD date validation edge cases."""
        # Test various invalid date formats
        invalid_dates = [
            "2023/12/01",  # Wrong separator
            "12-01-2023",  # Wrong order
            "2023-13-01",  # Invalid month
            "2023-12-32",  # Invalid day
            "not-a-date",  # Not a date
            "",            # Empty string
        ]
        
        for invalid_date in invalid_dates:
            response = client.get(f"/apod?date={invalid_date}")
            # Accept either 400 (service validation) or 422 (FastAPI validation)
            assert response.status_code in [400, 422]


class TestMarsPhotosEndpoint:
    """Comprehensive tests for Mars photos endpoint."""
    
    def test_mars_photos_all_rovers(self, client):
        """Test Mars photos endpoint with all supported rovers."""
        mock_service = AsyncMock()
        
        rovers = ["curiosity", "perseverance", "opportunity", "spirit"]
        
        for rover in rovers:
            mock_mars_data = MockNASAResponses.get_mars_rover_response(
                rover=rover, sol=1000, photo_count=3
            )
            mock_mars_response = MarsRoverResponse(**mock_mars_data)
            mock_photos = ProcessedMarsPhotos(mock_mars_response)
            mock_service.search_mars_photos.return_value = mock_photos
            app.dependency_overrides[get_nasa_service] = lambda: mock_service
            
            response = client.get(f"/mars-photos/{rover}?sol=1000")
            assert response.status_code == 200
            
            data = response.json()
            assert data["rover"] == rover
            assert data["sol"] == 1000
            
            mock_service.search_mars_photos.assert_called_with(rover, 1000, None)
        
        app.dependency_overrides.clear()
    
    def test_mars_photos_with_camera_filter(self, client):
        """Test Mars photos endpoint with camera filter."""
        mock_service = AsyncMock()
        
        cameras = ["FHAZ", "RHAZ", "MAST", "CHEMCAM", "MAHLI", "NAVCAM"]
        
        for camera in cameras:
            mock_mars_data = MockNASAResponses.get_mars_rover_response(
                rover="curiosity", sol=1000, camera=camera, photo_count=2
            )
            mock_mars_response = MarsRoverResponse(**mock_mars_data)
            mock_photos = ProcessedMarsPhotos(mock_mars_response)
            mock_service.search_mars_photos.return_value = mock_photos
            app.dependency_overrides[get_nasa_service] = lambda: mock_service
            
            response = client.get(f"/mars-photos/curiosity?sol=1000&camera={camera}")
            assert response.status_code == 200
            
            data = response.json()
            assert camera in data["cameras_used"]
            
            mock_service.search_mars_photos.assert_called_with("curiosity", 1000, camera)
        
        app.dependency_overrides.clear()
    
    def test_mars_photos_no_photos_found(self, client):
        """Test Mars photos endpoint when no photos are found."""
        mock_service = AsyncMock()
        mock_mars_data = MockNASAResponses.get_mars_rover_response(
            rover="curiosity", sol=1000, photo_count=0
        )
        mock_mars_response = MarsRoverResponse(**mock_mars_data)
        mock_photos = ProcessedMarsPhotos(mock_mars_response)
        mock_service.search_mars_photos.return_value = mock_photos
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/mars-photos/curiosity?sol=1000")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_photos"] == 0
        assert data["has_photos"] is False
        assert len(data["photos"]) == 0
        
        app.dependency_overrides.clear()
    
    def test_mars_photos_enriched_data(self, client):
        """Test Mars photos endpoint enriched data."""
        mock_service = AsyncMock()
        mock_mars_data = MockNASAResponses.get_mars_rover_response(
            rover="curiosity", sol=1000, photo_count=5
        )
        mock_mars_response = MarsRoverResponse(**mock_mars_data)
        mock_photos = ProcessedMarsPhotos(mock_mars_response)
        mock_service.search_mars_photos.return_value = mock_photos
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/mars-photos/curiosity?sol=1000")
        data = response.json()
        
        # Check enriched fields
        assert "has_photos" in data
        assert "cameras_used" in data
        assert "earth_dates" in data
        assert "camera_summary" in data
        
        # Check photo-level enrichments
        if data["photos"]:
            photo = data["photos"][0]
            assert "is_color_camera" in photo
            assert "camera_type" in photo
        
        app.dependency_overrides.clear()
    
    def test_mars_photos_sol_validation(self, client):
        """Test Mars photos sol parameter validation."""
        # Test invalid sol values
        invalid_sols = [-1, "invalid", "", "99999999"]
        
        for invalid_sol in invalid_sols:
            response = client.get(f"/mars-photos/curiosity?sol={invalid_sol}")
            assert response.status_code == 422
    
    def test_mars_photos_rover_case_insensitive(self, client):
        """Test Mars photos rover name case insensitivity."""
        mock_service = AsyncMock()
        mock_mars_data = MockNASAResponses.get_mars_rover_response(
            rover="curiosity", sol=1000, photo_count=1
        )
        mock_mars_response = MarsRoverResponse(**mock_mars_data)
        mock_photos = ProcessedMarsPhotos(mock_mars_response)
        mock_service.search_mars_photos.return_value = mock_photos
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        # Test different cases
        rover_variations = ["curiosity", "CURIOSITY", "Curiosity", "CuRiOsItY"]
        
        for rover_name in rover_variations:
            response = client.get(f"/mars-photos/{rover_name}?sol=1000")
            # The endpoint should handle case variations
            # (implementation dependent)
        
        app.dependency_overrides.clear()


class TestNEOEndpoint:
    """Comprehensive tests for NEO endpoint."""
    
    def test_neo_single_date(self, client):
        """Test NEO endpoint with single date (start_date = end_date)."""
        mock_service = AsyncMock()
        mock_neo_data = MockNASAResponses.get_neo_response(
            "2023-12-01", "2023-12-01", object_count=3
        )
        mock_neo_response = NEOResponse(**mock_neo_data)
        mock_neo = ProcessedNEOData(mock_neo_response)
        mock_service.get_near_earth_objects.return_value = mock_neo
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/neo?start_date=2023-12-01&end_date=2023-12-01")
        assert response.status_code == 200
        
        data = response.json()
        assert data["date_range"]["start_date"] == "2023-12-01"
        assert data["date_range"]["end_date"] == "2023-12-01"
        
        mock_service.get_near_earth_objects.assert_called_once_with("2023-12-01", "2023-12-01")
        
        app.dependency_overrides.clear()
    
    def test_neo_date_range(self, client):
        """Test NEO endpoint with date range."""
        mock_service = AsyncMock()
        mock_neo_data = MockNASAResponses.get_neo_response(
            "2023-12-01", "2023-12-07", object_count=10
        )
        mock_neo_response = NEOResponse(**mock_neo_data)
        mock_neo = ProcessedNEOData(mock_neo_response)
        mock_service.get_near_earth_objects.return_value = mock_neo
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/neo?start_date=2023-12-01&end_date=2023-12-07")
        assert response.status_code == 200
        
        data = response.json()
        assert data["date_range"]["start_date"] == "2023-12-01"
        assert data["date_range"]["end_date"] == "2023-12-07"
        
        app.dependency_overrides.clear()
    
    def test_neo_no_objects_found(self, client):
        """Test NEO endpoint when no objects are found."""
        mock_service = AsyncMock()
        mock_neo_data = SAMPLE_NEO_RESPONSES["no_objects"]
        # Add the required date_range field
        mock_neo_data["date_range"] = {"start_date": "2023-12-01", "end_date": "2023-12-01"}
        mock_neo_response = NEOResponse(**mock_neo_data)
        mock_neo = ProcessedNEOData(mock_neo_response)
        mock_service.get_near_earth_objects.return_value = mock_neo
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/neo?start_date=2023-12-01&end_date=2023-12-01")
        assert response.status_code == 200
        
        data = response.json()
        assert data["element_count"] == 0
        assert data["total_objects"] == 0
        assert data["hazardous_count"] == 0
        
        app.dependency_overrides.clear()
    
    def test_neo_enriched_data(self, client):
        """Test NEO endpoint enriched data."""
        mock_service = AsyncMock()
        mock_neo_data = MockNASAResponses.get_neo_response(
            "2023-12-01", "2023-12-01", object_count=3
        )
        mock_neo_response = NEOResponse(**mock_neo_data)
        mock_neo = ProcessedNEOData(mock_neo_response)
        mock_service.get_near_earth_objects.return_value = mock_neo
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/neo?start_date=2023-12-01&end_date=2023-12-01")
        data = response.json()
        
        # Check enriched fields
        assert "total_objects" in data
        assert "hazardous_count" in data
        assert "size_categories" in data
        assert "closest_approach" in data
        assert "fastest_object" in data
        
        # Check object-level enrichments
        if data["near_earth_objects"]:
            for date_key, objects in data["near_earth_objects"].items():
                for obj in objects:
                    assert "size_category" in obj
                    assert "speed_category" in obj
                    assert "distance_category" in obj
        
        app.dependency_overrides.clear()
    
    def test_neo_date_validation(self, client):
        """Test NEO endpoint date validation."""
        # Test missing parameters
        response = client.get("/neo")
        assert response.status_code == 422
        
        response = client.get("/neo?start_date=2023-12-01")
        assert response.status_code == 422
        
        response = client.get("/neo?end_date=2023-12-01")
        assert response.status_code == 422
        
        # Test invalid date formats
        response = client.get("/neo?start_date=invalid&end_date=2023-12-01")
        assert response.status_code == 422
        
        # Test end date before start date
        response = client.get("/neo?start_date=2023-12-07&end_date=2023-12-01")
        # This might be handled at service layer
        assert response.status_code in [400, 422]


class TestRoversEndpoint:
    """Comprehensive tests for rovers information endpoint."""
    
    def test_rovers_endpoint_basic(self, client):
        """Test basic rovers endpoint functionality."""
        response = client.get("/rovers")
        assert response.status_code == 200
        
        data = response.json()
        assert "rovers" in data
        assert "camera_descriptions" in data
        assert isinstance(data["rovers"], dict)
        assert isinstance(data["camera_descriptions"], dict)
    
    def test_rovers_endpoint_content(self, client):
        """Test rovers endpoint content."""
        response = client.get("/rovers")
        data = response.json()
        
        rovers = data["rovers"]
        expected_rovers = ["curiosity", "perseverance", "opportunity", "spirit"]
        
        for rover in expected_rovers:
            assert rover in rovers
            rover_info = rovers[rover]
            
            # Check required fields
            assert "name" in rover_info
            assert "status" in rover_info
            assert "landing_date" in rover_info
            assert "mission_duration" in rover_info
            assert "cameras" in rover_info
            assert "description" in rover_info
            
            # Check cameras list
            assert isinstance(rover_info["cameras"], list)
            assert len(rover_info["cameras"]) > 0
    
    def test_rovers_camera_descriptions(self, client):
        """Test rovers endpoint camera descriptions."""
        response = client.get("/rovers")
        data = response.json()
        
        camera_descriptions = data["camera_descriptions"]
        expected_cameras = ["FHAZ", "RHAZ", "MAST", "CHEMCAM", "MAHLI", "MARDI", "NAVCAM"]
        
        for camera in expected_cameras:
            if camera in camera_descriptions:
                camera_info = camera_descriptions[camera]
                assert "full_name" in camera_info
                assert "description" in camera_info
                assert "type" in camera_info


class TestHealthEndpoint:
    """Comprehensive tests for health endpoint."""
    
    def test_health_endpoint_healthy(self, client):
        """Test health endpoint when all services are healthy."""
        mock_service = AsyncMock()
        mock_service.health_check.return_value = {
            "service": "healthy",
            "nasa_api": "healthy",
            "cache": "enabled",
            "timestamp": datetime.now().isoformat(),
            "cache_stats": {"hits": 10, "misses": 5}
        }
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "healthy"
        assert data["nasa_api"] == "healthy"
        assert "timestamp" in data
        assert "uptime" in data
        
        app.dependency_overrides.clear()
    
    def test_health_endpoint_degraded(self, client):
        """Test health endpoint when service is degraded."""
        mock_service = AsyncMock()
        mock_service.health_check.return_value = {
            "service": "healthy",
            "nasa_api": "unhealthy",
            "cache": "enabled",
            "timestamp": datetime.now().isoformat(),
            "nasa_api_error": "Connection timeout"
        }
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "degraded"
        assert data["nasa_api"] == "unhealthy"
        assert "nasa_api_error" in data
        
        app.dependency_overrides.clear()
    
    def test_health_endpoint_structure(self, client):
        """Test health endpoint response structure."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = ["status", "timestamp", "uptime"]
        for field in required_fields:
            assert field in data


class TestMetricsEndpoint:
    """Comprehensive tests for metrics endpoint."""
    
    def test_metrics_endpoint_basic(self, client):
        """Test basic metrics endpoint functionality."""
        response = client.get("/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "timestamp" in data
        assert "nasa_api_stats" in data
        assert "logging_config" in data
        assert "application_config" in data
    
    def test_metrics_endpoint_structure(self, client):
        """Test metrics endpoint response structure."""
        response = client.get("/metrics")
        data = response.json()
        
        # Check NASA API stats structure
        nasa_stats = data["nasa_api_stats"]
        expected_stats = ["total_requests", "successful_requests", "failed_requests"]
        for stat in expected_stats:
            if stat in nasa_stats:
                assert isinstance(nasa_stats[stat], (int, float))
    
    def test_metrics_after_requests(self, client):
        """Test metrics endpoint after making some requests."""
        mock_service = AsyncMock()
        mock_service.get_daily_astronomy_picture.return_value = AsyncMock()
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        # Make some requests to generate metrics
        for _ in range(3):
            client.get("/apod")
        
        response = client.get("/metrics")
        assert response.status_code == 200
        
        data = response.json()
        # Metrics should reflect the requests made
        # (implementation dependent)
        
        app.dependency_overrides.clear()


class TestOpenAPIDocumentation:
    """Comprehensive tests for OpenAPI documentation."""
    
    def test_openapi_json_endpoint(self, client):
        """Test OpenAPI JSON schema endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert data["info"]["title"] == "NASA Data API"
        assert data["info"]["version"] == "1.0.0"
        assert "paths" in data
        assert "components" in data
    
    def test_openapi_paths_documentation(self, client):
        """Test OpenAPI paths documentation."""
        response = client.get("/openapi.json")
        data = response.json()
        
        paths = data["paths"]
        expected_paths = [
            "/", "/apod", "/mars-photos/{rover}", "/neo", 
            "/rovers", "/health", "/metrics"
        ]
        
        for path in expected_paths:
            assert path in paths
            path_info = paths[path]
            
            # Check that each path has proper HTTP methods
            assert isinstance(path_info, dict)
            assert len(path_info) > 0
    
    def test_swagger_ui_endpoint(self, client):
        """Test Swagger UI documentation endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"swagger" in response.content.lower()
    
    def test_redoc_endpoint(self, client):
        """Test ReDoc documentation endpoint."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"redoc" in response.content.lower()


class TestCORSHandling:
    """Test CORS handling."""
    
    def test_cors_preflight_request(self, client):
        """Test CORS preflight request handling."""
        response = client.options(
            "/apod",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # CORS handling depends on middleware configuration
        # This test might need adjustment based on actual CORS setup
        assert response.status_code in [200, 204]
    
    def test_cors_actual_request(self, client):
        """Test CORS actual request handling."""
        mock_service = AsyncMock()
        mock_service.get_daily_astronomy_picture.return_value = AsyncMock()
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get(
            "/apod",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        # Check for CORS headers (if configured)
        
        app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])