"""
Unit tests for NASA service layer.

This module contains comprehensive unit tests for the NASA service layer,
including business logic, data transformation, validation, and caching.
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from nasa_mcp_demo.services.nasa_service import (
    NASAService, 
    ProcessedAPOD, 
    ProcessedMarsPhotos, 
    ProcessedNEOData,
    SimpleCache,
    CacheEntry
)
from nasa_mcp_demo.models.config import AppConfig, NASAConfig, CacheConfig
from nasa_mcp_demo.models.errors import NASAAPIError, NASAAPIInvalidRequest
from nasa_mcp_demo.models.nasa_responses import (
    APODResponse, 
    MarsRoverResponse, 
    MarsPhoto,
    NEOResponse,
    NEOObject
)


class TestSimpleCache:
    """Test cases for SimpleCache class."""
    
    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = SimpleCache(max_size=100)
        assert cache.max_size == 100
        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0
    
    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = SimpleCache()
        
        # Set and get value
        cache.set("key1", "value1", ttl=60)
        result = cache.get("key1")
        assert result == "value1"
        
        # Get non-existent key
        result = cache.get("nonexistent")
        assert result is None
    
    def test_cache_expiration(self):
        """Test cache entry expiration."""
        cache = SimpleCache()
        
        # Set value with very short TTL
        cache.set("key1", "value1", ttl=0)
        
        # Should be expired immediately
        result = cache.get("key1")
        assert result is None
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = SimpleCache(max_size=2)
        
        # Fill cache to capacity
        cache.set("key1", "value1", ttl=60)
        cache.set("key2", "value2", ttl=60)
        
        # Access key1 to make it more recently used
        cache.get("key1")
        
        # Add third item, should evict key2 (least recently used)
        cache.set("key3", "value3", ttl=60)
        
        assert cache.get("key1") == "value1"  # Still there
        assert cache.get("key2") is None      # Evicted
        assert cache.get("key3") == "value3"  # New item


class TestCacheEntry:
    """Test cases for CacheEntry class."""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation."""
        entry = CacheEntry("test_data", ttl=60)
        assert entry.data == "test_data"
        assert entry.ttl == 60
        assert isinstance(entry.created_at, datetime)
    
    def test_cache_entry_expiration_check(self):
        """Test cache entry expiration checking."""
        # Create entry that should not be expired
        entry = CacheEntry("test_data", ttl=60)
        assert not entry.is_expired()
        
        # Create entry that should be expired
        expired_entry = CacheEntry("test_data", ttl=0)
        # Small delay to ensure expiration
        import time
        time.sleep(0.001)
        assert expired_entry.is_expired()


class TestProcessedAPOD:
    """Test cases for ProcessedAPOD class."""
    
    def test_processed_apod_creation(self):
        """Test ProcessedAPOD creation and enrichments."""
        apod_response = APODResponse(
            date="2023-12-01",
            title="Test APOD",
            explanation="This is a test astronomy picture with multiple words for testing.",
            url="https://example.com/image.jpg",
            media_type="image",
            copyright="Test Copyright",
            hdurl="https://example.com/hd_image.jpg"
        )
        
        processed = ProcessedAPOD(apod_response)
        
        # Check basic fields
        assert processed.date == "2023-12-01"
        assert processed.title == "Test APOD"
        assert processed.media_type == "image"
        
        # Check enrichments
        assert processed.is_image is True
        assert processed.is_video is False
        assert processed.has_hd_version is True
        assert processed.word_count == 11  # Count words in explanation
        assert processed.is_recent is False  # 2023 date should not be recent
    
    def test_processed_apod_video_type(self):
        """Test ProcessedAPOD with video media type."""
        apod_response = APODResponse(
            date=date.today().strftime('%Y-%m-%d'),
            title="Test Video APOD",
            explanation="Short explanation.",
            url="https://example.com/video.mp4",
            media_type="video"
        )
        
        processed = ProcessedAPOD(apod_response)
        
        assert processed.is_image is False
        assert processed.is_video is True
        assert processed.has_hd_version is False
        assert processed.is_recent is True  # Today's date should be recent
    
    def test_processed_apod_to_dict(self):
        """Test ProcessedAPOD to_dict conversion."""
        apod_response = APODResponse(
            date="2023-12-01",
            title="Test APOD",
            explanation="Test explanation.",
            url="https://example.com/image.jpg",
            media_type="image"
        )
        
        processed = ProcessedAPOD(apod_response)
        result_dict = processed.to_dict()
        
        # Check all expected keys are present
        expected_keys = {
            'date', 'title', 'explanation', 'url', 'media_type', 'copyright',
            'hdurl', 'is_image', 'is_video', 'has_hd_version', 'word_count', 'is_recent'
        }
        assert set(result_dict.keys()) == expected_keys


class TestProcessedMarsPhotos:
    """Test cases for ProcessedMarsPhotos class."""
    
    def test_processed_mars_photos_creation(self):
        """Test ProcessedMarsPhotos creation and enrichments."""
        mars_photos = [
            MarsPhoto(
                id=1,
                img_src="https://example.com/photo1.jpg",
                earth_date="2023-12-01",
                rover_name="curiosity",
                camera_name="MAST",
                camera_full_name="Mast Camera"
            ),
            MarsPhoto(
                id=2,
                img_src="https://example.com/photo2.jpg",
                earth_date="2023-12-01",
                rover_name="curiosity",
                camera_name="FHAZ",
                camera_full_name="Front Hazard Avoidance Camera"
            )
        ]
        
        mars_response = MarsRoverResponse(
            photos=mars_photos,
            rover="curiosity",
            sol=100,
            total_photos=2
        )
        
        processed = ProcessedMarsPhotos(mars_response)
        
        # Check basic fields
        assert processed.rover == "curiosity"
        assert processed.sol == 100
        assert processed.total_photos == 2
        assert len(processed.photos) == 2
        
        # Check enrichments
        assert processed.has_photos is True
        assert set(processed.cameras_used) == {"MAST", "FHAZ"}
        assert processed.earth_dates == ["2023-12-01"]
        assert processed.camera_summary == {"MAST": 1, "FHAZ": 1}
        
        # Check photo enrichments
        photo1 = processed.photos[0]
        assert photo1["is_color_camera"] is True  # MAST is color
        assert photo1["camera_type"] == "Mast Camera"
    
    def test_camera_type_classification(self):
        """Test camera type classification logic."""
        mars_photos = [
            MarsPhoto(
                id=1,
                img_src="https://example.com/photo1.jpg",
                earth_date="2023-12-01",
                rover_name="curiosity",
                camera_name="CHEMCAM",
                camera_full_name="Chemistry and Camera Complex"
            )
        ]
        
        mars_response = MarsRoverResponse(
            photos=mars_photos,
            rover="curiosity",
            sol=100,
            total_photos=1
        )
        
        processed = ProcessedMarsPhotos(mars_response)
        photo = processed.photos[0]
        
        assert photo["is_color_camera"] is False  # CHEMCAM is not color
        assert photo["camera_type"] == "Chemistry and Camera Complex"


class TestProcessedNEOData:
    """Test cases for ProcessedNEOData class."""
    
    def test_processed_neo_data_creation(self):
        """Test ProcessedNEOData creation and enrichments."""
        neo_objects = {
            "2023-12-01": [
                NEOObject(
                    id="1",
                    name="Test Asteroid 1",
                    estimated_diameter_km={
                        "estimated_diameter_min": 0.1,
                        "estimated_diameter_max": 0.2
                    },
                    is_potentially_hazardous=True,
                    close_approach_date="2023-12-01",
                    miss_distance_km=100000.0,
                    relative_velocity_kmh=25000.0
                ),
                NEOObject(
                    id="2",
                    name="Test Asteroid 2",
                    estimated_diameter_km={
                        "estimated_diameter_min": 1.0,
                        "estimated_diameter_max": 2.0
                    },
                    is_potentially_hazardous=False,
                    close_approach_date="2023-12-01",
                    miss_distance_km=500000.0,
                    relative_velocity_kmh=75000.0
                )
            ]
        }
        
        neo_response = NEOResponse(
            near_earth_objects=neo_objects,
            element_count=2,
            date_range={"start_date": "2023-12-01", "end_date": "2023-12-01"}
        )
        
        processed = ProcessedNEOData(neo_response)
        
        # Check basic fields
        assert processed.element_count == 2
        assert processed.total_objects == 2
        
        # Check enrichments
        assert processed.hazardous_count == 1
        assert "Medium" in processed.size_categories  # 0.15 km average
        assert "Large" in processed.size_categories   # 1.5 km average
        
        # Check closest and fastest objects
        assert processed.closest_approach is not None
        assert processed.fastest_object is not None
        assert processed.fastest_object["relative_velocity_kmh"] == 75000.0
    
    def test_neo_categorization(self):
        """Test NEO size, speed, and distance categorization."""
        neo_objects = {
            "2023-12-01": [
                NEOObject(
                    id="1",
                    name="Very Small Fast Asteroid",
                    estimated_diameter_km={
                        "estimated_diameter_min": 0.005,
                        "estimated_diameter_max": 0.008
                    },
                    is_potentially_hazardous=False,
                    close_approach_date="2023-12-01",
                    miss_distance_km=200000.0,  # Closer than moon (384400 km)
                    relative_velocity_kmh=150000.0  # Very fast
                )
            ]
        }
        
        neo_response = NEOResponse(
            near_earth_objects=neo_objects,
            element_count=1,
            date_range={"start_date": "2023-12-01", "end_date": "2023-12-01"}
        )
        
        processed = ProcessedNEOData(neo_response)
        neo_obj = processed.near_earth_objects["2023-12-01"][0]
        
        assert neo_obj["size_category"] == "Very Small"
        assert neo_obj["speed_category"] == "Very Fast"
        assert neo_obj["distance_category"] == "Closer than Moon"


@pytest.fixture
def mock_config():
    """Create mock configuration for testing."""
    return AppConfig(
        nasa=NASAConfig(api_key="test_key"),
        cache=CacheConfig(
            enable_caching=True,
            apod_cache_ttl=3600,
            mars_photos_cache_ttl=7200,
            neo_cache_ttl=1800,
            max_cache_size=100
        )
    )


@pytest.fixture
def mock_nasa_client():
    """Create mock NASA client for testing."""
    return AsyncMock()


class TestNASAService:
    """Test cases for NASAService class."""
    
    def test_service_initialization(self, mock_config):
        """Test service initialization."""
        service = NASAService(mock_config)
        
        assert service.config == mock_config
        assert service.cache_config == mock_config.cache
        assert service.cache is not None  # Cache should be enabled
    
    def test_service_initialization_no_cache(self, mock_config):
        """Test service initialization with caching disabled."""
        mock_config.cache.enable_caching = False
        service = NASAService(mock_config)
        
        assert service.cache is None
    
    @pytest.mark.asyncio
    async def test_get_daily_astronomy_picture_success(self, mock_config, mock_nasa_client):
        """Test successful APOD retrieval."""
        # Setup mock response
        mock_apod = APODResponse(
            date="2023-12-01",
            title="Test APOD",
            explanation="Test explanation.",
            url="https://example.com/image.jpg",
            media_type="image"
        )
        mock_nasa_client.get_apod.return_value = mock_apod
        
        service = NASAService(mock_config, mock_nasa_client)
        result = await service.get_daily_astronomy_picture("2023-12-01")
        
        assert isinstance(result, ProcessedAPOD)
        assert result.date == "2023-12-01"
        assert result.title == "Test APOD"
        mock_nasa_client.get_apod.assert_called_once_with("2023-12-01")
    
    @pytest.mark.asyncio
    async def test_get_daily_astronomy_picture_cached(self, mock_config, mock_nasa_client):
        """Test APOD retrieval from cache."""
        service = NASAService(mock_config, mock_nasa_client)
        
        # Pre-populate cache
        cached_apod = ProcessedAPOD(APODResponse(
            date="2023-12-01",
            title="Cached APOD",
            explanation="Cached explanation.",
            url="https://example.com/cached.jpg",
            media_type="image"
        ))
        cache_key = service._generate_cache_key("apod", date="2023-12-01")
        service._set_in_cache(cache_key, cached_apod, 3600)
        
        result = await service.get_daily_astronomy_picture("2023-12-01")
        
        assert result.title == "Cached APOD"
        # NASA client should not be called due to cache hit
        mock_nasa_client.get_apod.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_daily_astronomy_picture_invalid_date(self, mock_config, mock_nasa_client):
        """Test APOD retrieval with invalid date."""
        service = NASAService(mock_config, mock_nasa_client)
        
        with pytest.raises(NASAAPIInvalidRequest) as exc_info:
            await service.get_daily_astronomy_picture("invalid-date")
        
        assert "Invalid date format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_daily_astronomy_picture_future_date(self, mock_config, mock_nasa_client):
        """Test APOD retrieval with future date."""
        service = NASAService(mock_config, mock_nasa_client)
        future_date = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        with pytest.raises(NASAAPIInvalidRequest) as exc_info:
            await service.get_daily_astronomy_picture(future_date)
        
        assert "Date cannot be in the future" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_mars_photos_success(self, mock_config, mock_nasa_client):
        """Test successful Mars photos retrieval."""
        # Setup mock response
        mock_photos = [
            MarsPhoto(
                id=1,
                img_src="https://example.com/photo1.jpg",
                earth_date="2023-12-01",
                rover_name="curiosity",
                camera_name="MAST",
                camera_full_name="Mast Camera"
            )
        ]
        mock_response = MarsRoverResponse(
            photos=mock_photos,
            rover="curiosity",
            sol=100,
            total_photos=1
        )
        mock_nasa_client.get_mars_rover_photos.return_value = mock_response
        
        service = NASAService(mock_config, mock_nasa_client)
        result = await service.search_mars_photos("curiosity", 100, "MAST")
        
        assert isinstance(result, ProcessedMarsPhotos)
        assert result.rover == "curiosity"
        assert result.sol == 100
        assert len(result.photos) == 1
        mock_nasa_client.get_mars_rover_photos.assert_called_once_with("curiosity", 100, "MAST")
    
    @pytest.mark.asyncio
    async def test_search_mars_photos_invalid_rover(self, mock_config, mock_nasa_client):
        """Test Mars photos retrieval with invalid rover."""
        service = NASAService(mock_config, mock_nasa_client)
        
        with pytest.raises(NASAAPIInvalidRequest) as exc_info:
            await service.search_mars_photos("invalid_rover", 100)
        
        assert "Invalid rover name" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_mars_photos_invalid_sol(self, mock_config, mock_nasa_client):
        """Test Mars photos retrieval with invalid sol."""
        service = NASAService(mock_config, mock_nasa_client)
        
        with pytest.raises(NASAAPIInvalidRequest) as exc_info:
            await service.search_mars_photos("curiosity", -1)
        
        assert "Sol cannot be negative" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_near_earth_objects_success(self, mock_config, mock_nasa_client):
        """Test successful NEO data retrieval."""
        # Setup mock response
        neo_objects = {
            "2023-12-01": [
                NEOObject(
                    id="1",
                    name="Test Asteroid",
                    estimated_diameter_km={
                        "estimated_diameter_min": 0.1,
                        "estimated_diameter_max": 0.2
                    },
                    is_potentially_hazardous=False,
                    close_approach_date="2023-12-01",
                    miss_distance_km=100000.0,
                    relative_velocity_kmh=25000.0
                )
            ]
        }
        mock_response = NEOResponse(
            near_earth_objects=neo_objects,
            element_count=1,
            date_range={"start_date": "2023-12-01", "end_date": "2023-12-01"}
        )
        mock_nasa_client.get_neo_data.return_value = mock_response
        
        service = NASAService(mock_config, mock_nasa_client)
        result = await service.get_near_earth_objects("2023-12-01", "2023-12-01")
        
        assert isinstance(result, ProcessedNEOData)
        assert result.element_count == 1
        assert result.total_objects == 1
        mock_nasa_client.get_neo_data.assert_called_once_with("2023-12-01", "2023-12-01")
    
    @pytest.mark.asyncio
    async def test_get_near_earth_objects_invalid_date_range(self, mock_config, mock_nasa_client):
        """Test NEO data retrieval with invalid date range."""
        service = NASAService(mock_config, mock_nasa_client)
        
        with pytest.raises(NASAAPIInvalidRequest) as exc_info:
            await service.get_near_earth_objects("2023-12-08", "2023-12-01")  # End before start
        
        assert "Start date" in str(exc_info.value) and "cannot be after end date" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_near_earth_objects_date_range_too_large(self, mock_config, mock_nasa_client):
        """Test NEO data retrieval with date range too large."""
        service = NASAService(mock_config, mock_nasa_client)
        
        with pytest.raises(NASAAPIInvalidRequest) as exc_info:
            await service.get_near_earth_objects("2023-12-01", "2023-12-10")  # 9 days > 7 day limit
        
        assert "Date range cannot exceed 7 days" in str(exc_info.value)
    
    def test_validate_apod_date_valid(self, mock_config):
        """Test APOD date validation with valid dates."""
        service = NASAService(mock_config)
        
        # Valid date
        result = service._validate_apod_date("2023-12-01")
        assert result == "2023-12-01"
        
        # None (today)
        result = service._validate_apod_date(None)
        assert result is None
    
    def test_validate_apod_date_invalid(self, mock_config):
        """Test APOD date validation with invalid dates."""
        service = NASAService(mock_config)
        
        # Invalid format
        with pytest.raises(NASAAPIInvalidRequest):
            service._validate_apod_date("2023/12/01")
        
        # Future date
        future_date = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        with pytest.raises(NASAAPIInvalidRequest):
            service._validate_apod_date(future_date)
        
        # Before APOD service started
        with pytest.raises(NASAAPIInvalidRequest):
            service._validate_apod_date("1990-01-01")
    
    def test_validate_rover_name(self, mock_config):
        """Test rover name validation."""
        service = NASAService(mock_config)
        
        # Valid rovers
        assert service._validate_rover_name("curiosity") == "curiosity"
        assert service._validate_rover_name("CURIOSITY") == "curiosity"
        assert service._validate_rover_name(" Perseverance ") == "perseverance"
        
        # Invalid rover
        with pytest.raises(NASAAPIInvalidRequest):
            service._validate_rover_name("invalid_rover")
        
        # Empty rover
        with pytest.raises(NASAAPIInvalidRequest):
            service._validate_rover_name("")
    
    def test_validate_sol(self, mock_config):
        """Test sol validation."""
        service = NASAService(mock_config)
        
        # Valid sols
        assert service._validate_sol(100) == 100
        assert service._validate_sol("100") == 100
        assert service._validate_sol(0) == 0
        
        # Invalid sols
        with pytest.raises(NASAAPIInvalidRequest):
            service._validate_sol(-1)
        
        with pytest.raises(NASAAPIInvalidRequest):
            service._validate_sol(20000)  # Too large
        
        with pytest.raises(NASAAPIInvalidRequest):
            service._validate_sol("invalid")
    
    def test_validate_camera_name(self, mock_config):
        """Test camera name validation."""
        service = NASAService(mock_config)
        
        # Valid cameras
        assert service._validate_camera_name("fhaz") == "FHAZ"
        assert service._validate_camera_name("MAST") == "MAST"
        assert service._validate_camera_name(" navcam ") == "NAVCAM"
        
        # Invalid camera
        with pytest.raises(NASAAPIInvalidRequest):
            service._validate_camera_name("invalid_camera")
        
        # Empty camera
        with pytest.raises(NASAAPIInvalidRequest):
            service._validate_camera_name("")
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_config, mock_nasa_client):
        """Test successful health check."""
        mock_nasa_client.health_check.return_value = True
        
        service = NASAService(mock_config, mock_nasa_client)
        result = await service.health_check()
        
        assert result["service"] == "healthy"
        assert result["nasa_api"] == "healthy"
        assert result["cache"] == "enabled"
        assert "timestamp" in result
        assert "cache_stats" in result
    
    @pytest.mark.asyncio
    async def test_health_check_api_failure(self, mock_config, mock_nasa_client):
        """Test health check with API failure."""
        mock_nasa_client.health_check.side_effect = Exception("API Error")
        
        service = NASAService(mock_config, mock_nasa_client)
        result = await service.health_check()
        
        assert result["service"] == "healthy"
        assert result["nasa_api"] == "unhealthy"
        assert "nasa_api_error" in result
    
    def test_cache_key_generation(self, mock_config):
        """Test cache key generation."""
        service = NASAService(mock_config)
        
        # Same parameters should generate same key
        key1 = service._generate_cache_key("test", param1="value1", param2="value2")
        key2 = service._generate_cache_key("test", param2="value2", param1="value1")
        assert key1 == key2
        
        # Different parameters should generate different keys
        key3 = service._generate_cache_key("test", param1="different", param2="value2")
        assert key1 != key3
    
    def test_cache_operations(self, mock_config):
        """Test cache get and set operations."""
        service = NASAService(mock_config)
        
        # Test cache miss
        result = service._get_from_cache("nonexistent")
        assert result is None
        
        # Test cache set and hit
        service._set_in_cache("test_key", "test_value", 60)
        result = service._get_from_cache("test_key")
        assert result == "test_value"
    
    def test_cache_disabled(self, mock_config):
        """Test service behavior with caching disabled."""
        mock_config.cache.enable_caching = False
        service = NASAService(mock_config)
        
        # Cache operations should be no-ops
        service._set_in_cache("test_key", "test_value", 60)
        result = service._get_from_cache("test_key")
        assert result is None