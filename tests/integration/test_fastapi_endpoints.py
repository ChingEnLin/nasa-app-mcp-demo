"""
Integration tests for FastAPI endpoints.

Tests the REST API endpoints to ensure they work correctly with the NASA service.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime

from nasa_mcp_demo.main import app, get_nasa_service, get_app_config
from nasa_mcp_demo.services.nasa_service import ProcessedAPOD, ProcessedMarsPhotos, ProcessedNEOData
from nasa_mcp_demo.models.nasa_responses import APODResponse, MarsRoverResponse, NEOResponse


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from nasa_mcp_demo.models.config import AppConfig
    from nasa_mcp_demo.services.nasa_service import NASAService
    
    # Create test configuration
    test_config = AppConfig()
    test_service = NASAService(test_config)
    
    # Override dependencies
    app.dependency_overrides[get_nasa_service] = lambda: test_service
    app.dependency_overrides[get_app_config] = lambda: test_config
    
    client = TestClient(app)
    
    yield client
    
    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def mock_apod_response():
    """Mock APOD response data."""
    return APODResponse(
        date="2024-01-15",
        title="Test Astronomy Picture",
        explanation="This is a test explanation for the astronomy picture.",
        url="https://example.com/image.jpg",
        media_type="image",
        copyright="Test Copyright",
        hdurl="https://example.com/hd_image.jpg"
    )


@pytest.fixture
def mock_mars_response():
    """Mock Mars rover response data."""
    return MarsRoverResponse(
        photos=[],
        rover="curiosity",
        sol=1000,
        total_photos=0
    )


@pytest.fixture
def mock_neo_response():
    """Mock NEO response data."""
    return NEOResponse(
        near_earth_objects={},
        element_count=0,
        date_range={"start_date": "2024-01-01", "end_date": "2024-01-07"}
    )


class TestRootEndpoint:
    """Test the root endpoint."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "NASA Data API"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "nasa_apis" in data


class TestHealthEndpoint:
    """Test the health check endpoint."""
    
    def test_health_check_healthy(self, client):
        """Test health check when service is healthy."""
        # Create a mock service
        mock_service = AsyncMock()
        mock_service.health_check = AsyncMock(return_value={
            "service": "healthy",
            "nasa_api": "healthy",
            "cache": "enabled",
            "timestamp": datetime.now().isoformat()
        })
        
        # Override the dependency
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "healthy"
        assert data["nasa_api"] == "healthy"
    
    def test_health_check_degraded(self, client):
        """Test health check when NASA API is unhealthy."""
        # Create a mock service
        mock_service = AsyncMock()
        mock_service.health_check = AsyncMock(return_value={
            "service": "healthy",
            "nasa_api": "unhealthy",
            "cache": "enabled",
            "timestamp": datetime.now().isoformat(),
            "nasa_api_error": "Connection timeout"
        })
        
        # Override the dependency
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "degraded"
        assert data["nasa_api"] == "unhealthy"
        assert data["nasa_api_error"] == "Connection timeout"


class TestAPODEndpoint:
    """Test the APOD endpoint."""
    
    def test_get_apod_success(self, client, mock_apod_response):
        """Test successful APOD retrieval."""
        # Create processed APOD
        processed_apod = ProcessedAPOD(mock_apod_response)
        
        # Create mock service
        mock_service = AsyncMock()
        mock_service.get_daily_astronomy_picture = AsyncMock(return_value=processed_apod)
        
        # Override the dependency
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/apod")
        assert response.status_code == 200
        
        data = response.json()
        assert data["date"] == "2024-01-15"
        assert data["title"] == "Test Astronomy Picture"
        assert data["media_type"] == "image"
        assert data["is_image"] is True
        assert data["is_video"] is False
    
    def test_get_apod_with_date(self, client, mock_apod_response):
        """Test APOD retrieval with specific date."""
        processed_apod = ProcessedAPOD(mock_apod_response)
        
        # Create mock service
        mock_service = AsyncMock()
        mock_service.get_daily_astronomy_picture = AsyncMock(return_value=processed_apod)
        
        # Override the dependency
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/apod?date=2024-01-15")
        assert response.status_code == 200
        
        # Verify the service was called with the correct date
        mock_service.get_daily_astronomy_picture.assert_called_once_with("2024-01-15")
    
    def test_get_apod_invalid_date_format(self, client):
        """Test APOD with invalid date format."""
        response = client.get("/apod?date=invalid-date")
        assert response.status_code == 422  # Validation error


class TestMarsPhotosEndpoint:
    """Test the Mars photos endpoint."""
    
    def test_get_mars_photos_success(self, client, mock_mars_response):
        """Test successful Mars photos retrieval."""
        processed_photos = ProcessedMarsPhotos(mock_mars_response)
        
        # Create mock service
        mock_service = AsyncMock()
        mock_service.search_mars_photos = AsyncMock(return_value=processed_photos)
        
        # Override the dependency
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/mars-photos/curiosity?sol=1000")
        assert response.status_code == 200
        
        data = response.json()
        assert data["rover"] == "curiosity"
        assert data["sol"] == 1000
        assert data["total_photos"] == 0
        assert data["has_photos"] is False
    
    def test_get_mars_photos_with_camera(self, client, mock_mars_response):
        """Test Mars photos retrieval with camera filter."""
        processed_photos = ProcessedMarsPhotos(mock_mars_response)
        
        # Create mock service
        mock_service = AsyncMock()
        mock_service.search_mars_photos = AsyncMock(return_value=processed_photos)
        
        # Override the dependency
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/mars-photos/curiosity?sol=1000&camera=MAST")
        assert response.status_code == 200
        
        # Verify the service was called with correct parameters
        mock_service.search_mars_photos.assert_called_once_with("curiosity", 1000, "MAST")
    
    def test_get_mars_photos_missing_sol(self, client):
        """Test Mars photos without required sol parameter."""
        response = client.get("/mars-photos/curiosity")
        assert response.status_code == 422  # Validation error
    
    def test_get_mars_photos_invalid_sol(self, client):
        """Test Mars photos with invalid sol parameter."""
        response = client.get("/mars-photos/curiosity?sol=-1")
        assert response.status_code == 422  # Validation error


class TestNEOEndpoint:
    """Test the NEO endpoint."""
    
    def test_get_neo_success(self, client, mock_neo_response):
        """Test successful NEO data retrieval."""
        processed_neo = ProcessedNEOData(mock_neo_response)
        
        # Create mock service
        mock_service = AsyncMock()
        mock_service.get_near_earth_objects = AsyncMock(return_value=processed_neo)
        
        # Override the dependency
        app.dependency_overrides[get_nasa_service] = lambda: mock_service
        
        response = client.get("/neo?start_date=2024-01-01&end_date=2024-01-07")
        assert response.status_code == 200
        
        data = response.json()
        assert data["element_count"] == 0
        assert data["total_objects"] == 0
        assert data["date_range"]["start_date"] == "2024-01-01"
        assert data["date_range"]["end_date"] == "2024-01-07"
    
    def test_get_neo_missing_dates(self, client):
        """Test NEO endpoint without required date parameters."""
        response = client.get("/neo")
        assert response.status_code == 422  # Validation error
    
    def test_get_neo_invalid_date_format(self, client):
        """Test NEO endpoint with invalid date format."""
        response = client.get("/neo?start_date=invalid&end_date=2024-01-07")
        assert response.status_code == 422  # Validation error


class TestRoversEndpoint:
    """Test the rovers information endpoint."""
    
    def test_get_available_rovers(self, client):
        """Test rovers information endpoint."""
        response = client.get("/rovers")
        assert response.status_code == 200
        
        data = response.json()
        assert "rovers" in data
        assert "camera_descriptions" in data
        
        # Check that all expected rovers are present
        rovers = data["rovers"]
        assert "curiosity" in rovers
        assert "perseverance" in rovers
        assert "opportunity" in rovers
        assert "spirit" in rovers
        
        # Check rover data structure
        curiosity = rovers["curiosity"]
        assert curiosity["name"] == "Curiosity"
        assert curiosity["status"] == "active"
        assert "cameras" in curiosity
        assert "description" in curiosity


class TestErrorHandling:
    """Test error handling in endpoints."""
    
    def test_404_endpoint(self, client):
        """Test non-existent endpoint returns 404."""
        response = client.get("/non-existent")
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Test wrong HTTP method returns 405."""
        response = client.post("/apod")
        assert response.status_code == 405


class TestOpenAPIDocumentation:
    """Test OpenAPI documentation endpoints."""
    
    def test_openapi_json(self, client):
        """Test OpenAPI JSON schema endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        data = response.json()
        assert data["info"]["title"] == "NASA Data API"
        assert data["info"]["version"] == "1.0.0"
        assert "paths" in data
    
    def test_docs_endpoint(self, client):
        """Test Swagger UI documentation endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_endpoint(self, client):
        """Test ReDoc documentation endpoint."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]