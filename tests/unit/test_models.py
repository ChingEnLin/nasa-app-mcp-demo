"""
Unit tests for data models and validation.

This module contains comprehensive tests for all Pydantic models including
NASA API response models, configuration models, and error models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from nasa_mcp_demo.models import (
    APODResponse,
    AppConfig,
    CacheConfig,
    ConfigurationError,
    ErrorResponse,
    LoggingConfig,
    MarsPhoto,
    MarsRoverResponse,
    NASAAPIError,
    NASAAPIInvalidRequest,
    NASAAPIRateLimited,
    NASAAPITimeout,
    NASAAPIUnavailable,
    NASAConfig,
    NEOObject,
    NEOResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
)


class TestAPODResponse:
    """Tests for APODResponse model."""
    
    def test_valid_apod_response(self):
        """Test valid APOD response creation."""
        data = {
            "date": "2023-12-01",
            "title": "Test APOD",
            "explanation": "A test astronomy picture",
            "url": "https://example.com/image.jpg",
            "media_type": "image",
            "copyright": "NASA",
            "hdurl": "https://example.com/hd_image.jpg"
        }
        
        apod = APODResponse(**data)
        assert apod.date == "2023-12-01"
        assert apod.title == "Test APOD"
        assert apod.media_type == "image"
        assert apod.copyright == "NASA"
    
    def test_apod_response_without_optional_fields(self):
        """Test APOD response without optional fields."""
        data = {
            "date": "2023-12-01",
            "title": "Test APOD",
            "explanation": "A test astronomy picture",
            "url": "https://example.com/image.jpg",
            "media_type": "video"
        }
        
        apod = APODResponse(**data)
        assert apod.copyright is None
        assert apod.hdurl is None
        assert apod.media_type == "video"
    
    def test_invalid_media_type(self):
        """Test validation error for invalid media type."""
        data = {
            "date": "2023-12-01",
            "title": "Test APOD",
            "explanation": "A test astronomy picture",
            "url": "https://example.com/image.jpg",
            "media_type": "audio"  # Invalid
        }
        
        with pytest.raises(ValidationError) as exc_info:
            APODResponse(**data)
        
        assert "media_type must be either" in str(exc_info.value)
    
    def test_invalid_date_format(self):
        """Test validation error for invalid date format."""
        data = {
            "date": "12/01/2023",  # Invalid format
            "title": "Test APOD",
            "explanation": "A test astronomy picture",
            "url": "https://example.com/image.jpg",
            "media_type": "image"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            APODResponse(**data)
        
        assert "date must be in YYYY-MM-DD format" in str(exc_info.value)
    
    def test_invalid_url(self):
        """Test validation error for invalid URL."""
        data = {
            "date": "2023-12-01",
            "title": "Test APOD",
            "explanation": "A test astronomy picture",
            "url": "not-a-valid-url",  # Invalid URL
            "media_type": "image"
        }
        
        with pytest.raises(ValidationError):
            APODResponse(**data)


class TestMarsPhoto:
    """Tests for MarsPhoto model."""
    
    def test_valid_mars_photo(self):
        """Test valid Mars photo creation."""
        data = {
            "id": 12345,
            "img_src": "https://example.com/mars_photo.jpg",
            "earth_date": "2023-12-01",
            "rover_name": "curiosity",
            "camera_name": "MAST",
            "camera_full_name": "Mast Camera"
        }
        
        photo = MarsPhoto(**data)
        assert photo.id == 12345
        assert photo.rover_name == "curiosity"
        assert photo.earth_date == "2023-12-01"
    
    def test_rover_name_normalization(self):
        """Test rover name is normalized to lowercase."""
        data = {
            "id": 12345,
            "img_src": "https://example.com/mars_photo.jpg",
            "earth_date": "2023-12-01",
            "rover_name": "CURIOSITY",  # Uppercase
            "camera_name": "MAST",
            "camera_full_name": "Mast Camera"
        }
        
        photo = MarsPhoto(**data)
        assert photo.rover_name == "curiosity"  # Should be lowercase
    
    def test_invalid_rover_name(self):
        """Test validation error for invalid rover name."""
        data = {
            "id": 12345,
            "img_src": "https://example.com/mars_photo.jpg",
            "earth_date": "2023-12-01",
            "rover_name": "invalid_rover",
            "camera_name": "MAST",
            "camera_full_name": "Mast Camera"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            MarsPhoto(**data)
        
        assert "rover_name must be one of" in str(exc_info.value)
    
    def test_invalid_earth_date_format(self):
        """Test validation error for invalid earth date format."""
        data = {
            "id": 12345,
            "img_src": "https://example.com/mars_photo.jpg",
            "earth_date": "12/01/2023",  # Invalid format
            "rover_name": "curiosity",
            "camera_name": "MAST",
            "camera_full_name": "Mast Camera"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            MarsPhoto(**data)
        
        assert "earth_date must be in YYYY-MM-DD format" in str(exc_info.value)


class TestMarsRoverResponse:
    """Tests for MarsRoverResponse model."""
    
    def test_valid_mars_rover_response(self):
        """Test valid Mars rover response creation."""
        photo_data = {
            "id": 12345,
            "img_src": "https://example.com/mars_photo.jpg",
            "earth_date": "2023-12-01",
            "rover_name": "curiosity",
            "camera_name": "MAST",
            "camera_full_name": "Mast Camera"
        }
        
        data = {
            "photos": [photo_data],
            "rover": "curiosity",
            "sol": 100,
            "total_photos": 1
        }
        
        response = MarsRoverResponse(**data)
        assert len(response.photos) == 1
        assert response.rover == "curiosity"
        assert response.sol == 100
        assert response.total_photos == 1
    
    def test_negative_sol_validation(self):
        """Test validation error for negative sol value."""
        data = {
            "photos": [],
            "rover": "curiosity",
            "sol": -1,  # Invalid
            "total_photos": 0
        }
        
        with pytest.raises(ValidationError):
            MarsRoverResponse(**data)
    
    def test_negative_total_photos_validation(self):
        """Test validation error for negative total_photos value."""
        data = {
            "photos": [],
            "rover": "curiosity",
            "sol": 100,
            "total_photos": -1  # Invalid
        }
        
        with pytest.raises(ValidationError):
            MarsRoverResponse(**data)


class TestNEOObject:
    """Tests for NEOObject model."""
    
    def test_valid_neo_object(self):
        """Test valid NEO object creation."""
        data = {
            "id": "12345",
            "name": "Test Asteroid",
            "estimated_diameter_km": {
                "estimated_diameter_min": 0.1,
                "estimated_diameter_max": 0.5
            },
            "is_potentially_hazardous": False,
            "close_approach_date": "2023-12-01",
            "miss_distance_km": 1000000.0,
            "relative_velocity_kmh": 50000.0
        }
        
        neo = NEOObject(**data)
        assert neo.id == "12345"
        assert neo.name == "Test Asteroid"
        assert not neo.is_potentially_hazardous
        assert neo.miss_distance_km == 1000000.0
    
    def test_invalid_diameter_range_keys(self):
        """Test validation error for missing diameter range keys."""
        data = {
            "id": "12345",
            "name": "Test Asteroid",
            "estimated_diameter_km": {
                "min": 0.1,  # Wrong key
                "max": 0.5   # Wrong key
            },
            "is_potentially_hazardous": False,
            "close_approach_date": "2023-12-01",
            "miss_distance_km": 1000000.0,
            "relative_velocity_kmh": 50000.0
        }
        
        with pytest.raises(ValidationError) as exc_info:
            NEOObject(**data)
        
        assert "estimated_diameter_km must contain keys" in str(exc_info.value)
    
    def test_invalid_diameter_range_values(self):
        """Test validation error for invalid diameter range values."""
        data = {
            "id": "12345",
            "name": "Test Asteroid",
            "estimated_diameter_km": {
                "estimated_diameter_min": 0.5,
                "estimated_diameter_max": 0.1  # Max < Min
            },
            "is_potentially_hazardous": False,
            "close_approach_date": "2023-12-01",
            "miss_distance_km": 1000000.0,
            "relative_velocity_kmh": 50000.0
        }
        
        with pytest.raises(ValidationError) as exc_info:
            NEOObject(**data)
        
        assert "minimum diameter cannot be greater than maximum diameter" in str(exc_info.value)
    
    def test_negative_distance_validation(self):
        """Test validation error for negative miss distance."""
        data = {
            "id": "12345",
            "name": "Test Asteroid",
            "estimated_diameter_km": {
                "estimated_diameter_min": 0.1,
                "estimated_diameter_max": 0.5
            },
            "is_potentially_hazardous": False,
            "close_approach_date": "2023-12-01",
            "miss_distance_km": -1000.0,  # Invalid
            "relative_velocity_kmh": 50000.0
        }
        
        with pytest.raises(ValidationError):
            NEOObject(**data)


class TestNEOResponse:
    """Tests for NEOResponse model."""
    
    def test_valid_neo_response(self):
        """Test valid NEO response creation."""
        neo_data = {
            "id": "12345",
            "name": "Test Asteroid",
            "estimated_diameter_km": {
                "estimated_diameter_min": 0.1,
                "estimated_diameter_max": 0.5
            },
            "is_potentially_hazardous": False,
            "close_approach_date": "2023-12-01",
            "miss_distance_km": 1000000.0,
            "relative_velocity_kmh": 50000.0
        }
        
        data = {
            "near_earth_objects": {
                "2023-12-01": [neo_data]
            },
            "element_count": 1,
            "date_range": {
                "start_date": "2023-12-01",
                "end_date": "2023-12-01"
            }
        }
        
        response = NEOResponse(**data)
        assert response.element_count == 1
        assert "2023-12-01" in response.near_earth_objects
        assert len(response.near_earth_objects["2023-12-01"]) == 1
    
    def test_invalid_date_range_keys(self):
        """Test validation error for missing date range keys."""
        data = {
            "near_earth_objects": {},
            "element_count": 0,
            "date_range": {
                "from": "2023-12-01",  # Wrong key
                "to": "2023-12-01"     # Wrong key
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            NEOResponse(**data)
        
        assert "date_range must contain keys" in str(exc_info.value)
    
    def test_invalid_date_range_order(self):
        """Test validation error for invalid date range order."""
        data = {
            "near_earth_objects": {},
            "element_count": 0,
            "date_range": {
                "start_date": "2023-12-02",
                "end_date": "2023-12-01"  # End before start
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            NEOResponse(**data)
        
        assert "start_date cannot be after end_date" in str(exc_info.value)


class TestNASAConfig:
    """Tests for NASAConfig model."""
    
    def test_valid_nasa_config(self):
        """Test valid NASA config creation."""
        data = {
            "api_key": "test_key_123",
            "base_url": "https://api.nasa.gov",
            "timeout": 30,
            "max_retries": 3,
            "rate_limit_per_hour": 1000
        }
        
        config = NASAConfig(**data)
        assert config.api_key == "test_key_123"
        assert config.timeout == 30
        assert config.max_retries == 3
    
    def test_default_values(self):
        """Test default configuration values."""
        config = NASAConfig()
        assert config.api_key == "DEMO_KEY"
        assert config.base_url == "https://api.nasa.gov"
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.rate_limit_per_hour == 1000
    
    def test_empty_api_key_validation(self):
        """Test validation error for empty API key."""
        with pytest.raises(ValidationError) as exc_info:
            NASAConfig(api_key="")
        
        assert "api_key cannot be empty" in str(exc_info.value)
    
    def test_whitespace_api_key_validation(self):
        """Test validation error for whitespace-only API key."""
        with pytest.raises(ValidationError) as exc_info:
            NASAConfig(api_key="   ")
        
        assert "api_key cannot be empty" in str(exc_info.value)
    
    def test_api_key_strip(self):
        """Test API key whitespace stripping."""
        config = NASAConfig(api_key="  test_key  ")
        assert config.api_key == "test_key"
    
    def test_invalid_timeout_range(self):
        """Test validation error for invalid timeout values."""
        with pytest.raises(ValidationError):
            NASAConfig(timeout=0)  # Too low
        
        with pytest.raises(ValidationError):
            NASAConfig(timeout=301)  # Too high
    
    def test_invalid_max_retries_range(self):
        """Test validation error for invalid max_retries values."""
        with pytest.raises(ValidationError):
            NASAConfig(max_retries=-1)  # Too low
        
        with pytest.raises(ValidationError):
            NASAConfig(max_retries=11)  # Too high


class TestLoggingConfig:
    """Tests for LoggingConfig model."""
    
    def test_valid_logging_config(self):
        """Test valid logging config creation."""
        data = {
            "level": "DEBUG",
            "format": "json",
            "enable_request_logging": True,
            "enable_nasa_api_logging": False
        }
        
        config = LoggingConfig(**data)
        assert config.level == "DEBUG"
        assert config.format == "json"
        assert config.enable_request_logging is True
        assert config.enable_nasa_api_logging is False
    
    def test_default_values(self):
        """Test default logging configuration values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.format == "json"
        assert config.enable_request_logging is True
        assert config.enable_nasa_api_logging is True
    
    def test_log_level_normalization(self):
        """Test log level is normalized to uppercase."""
        config = LoggingConfig(level="debug")
        assert config.level == "DEBUG"
    
    def test_invalid_log_level(self):
        """Test validation error for invalid log level."""
        with pytest.raises(ValidationError) as exc_info:
            LoggingConfig(level="INVALID")
        
        assert "level must be one of" in str(exc_info.value)
    
    def test_log_format_normalization(self):
        """Test log format is normalized to lowercase."""
        config = LoggingConfig(format="JSON")
        assert config.format == "json"
    
    def test_invalid_log_format(self):
        """Test validation error for invalid log format."""
        with pytest.raises(ValidationError) as exc_info:
            LoggingConfig(format="xml")
        
        assert "format must be one of" in str(exc_info.value)


class TestCacheConfig:
    """Tests for CacheConfig model."""
    
    def test_valid_cache_config(self):
        """Test valid cache config creation."""
        data = {
            "enable_caching": True,
            "apod_cache_ttl": 7200,
            "mars_photos_cache_ttl": 3600,
            "neo_cache_ttl": 1800,
            "max_cache_size": 500
        }
        
        config = CacheConfig(**data)
        assert config.enable_caching is True
        assert config.apod_cache_ttl == 7200
        assert config.max_cache_size == 500
    
    def test_default_values(self):
        """Test default cache configuration values."""
        config = CacheConfig()
        assert config.enable_caching is True
        assert config.apod_cache_ttl == 3600
        assert config.mars_photos_cache_ttl == 7200
        assert config.neo_cache_ttl == 1800
        assert config.max_cache_size == 1000
    
    def test_invalid_ttl_values(self):
        """Test validation error for invalid TTL values."""
        with pytest.raises(ValidationError):
            CacheConfig(apod_cache_ttl=30)  # Too low
        
        with pytest.raises(ValidationError):
            CacheConfig(max_cache_size=5)  # Too low


class TestAppConfig:
    """Tests for AppConfig model."""
    
    def test_valid_app_config(self):
        """Test valid app config creation."""
        data = {
            "app_name": "Test App",
            "debug": True,
            "port": 8080,
            "enable_mcp": True
        }
        
        config = AppConfig(**data)
        assert config.app_name == "Test App"
        assert config.debug is True
        assert config.port == 8080
        assert config.enable_mcp is True
    
    def test_default_values(self):
        """Test default app configuration values."""
        config = AppConfig()
        assert config.app_name == "NASA MCP Demo"
        assert config.app_version == "1.0.0"
        assert config.debug is False
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.enable_mcp is False
    
    def test_nested_config_objects(self):
        """Test nested configuration objects are created."""
        config = AppConfig()
        assert isinstance(config.nasa, NASAConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.cache, CacheConfig)
    
    def test_invalid_port_range(self):
        """Test validation error for invalid port values."""
        with pytest.raises(ValidationError):
            AppConfig(port=0)  # Too low
        
        with pytest.raises(ValidationError):
            AppConfig(port=65536)  # Too high
    
    def test_cors_origins_validation(self):
        """Test CORS origins validation."""
        # Valid origins
        config = AppConfig(cors_origins=["http://localhost:3000", "https://example.com"])
        assert len(config.cors_origins) == 2
        
        # Wildcard is valid
        config = AppConfig(cors_origins=["*"])
        assert config.cors_origins == ["*"]
        
        # Invalid origin
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(cors_origins=["invalid-origin"])
        
        assert "Invalid CORS origin" in str(exc_info.value)
    
    def test_empty_cors_origins(self):
        """Test empty CORS origins defaults to wildcard."""
        config = AppConfig(cors_origins=[])
        assert config.cors_origins == ["*"]
    
    def test_get_nasa_api_key_method(self):
        """Test get_nasa_api_key method."""
        # With custom key
        config = AppConfig()
        config.nasa.api_key = "custom_key"
        assert config.get_nasa_api_key() == "custom_key"
        
        # With demo key
        config.nasa.api_key = "DEMO_KEY"
        assert config.get_nasa_api_key() == "DEMO_KEY"
    
    def test_is_demo_mode_method(self):
        """Test is_demo_mode method."""
        config = AppConfig()
        
        # Demo mode
        config.nasa.api_key = "DEMO_KEY"
        assert config.is_demo_mode() is True
        
        # Not demo mode
        config.nasa.api_key = "custom_key"
        assert config.is_demo_mode() is False
    
    def test_get_server_url_method(self):
        """Test get_server_url method."""
        config = AppConfig(host="localhost", port=8080)
        
        # Debug mode (HTTP)
        config.debug = True
        assert config.get_server_url() == "http://localhost:8080"
        
        # Production mode (HTTPS)
        config.debug = False
        assert config.get_server_url() == "https://localhost:8080"


class TestErrorModels:
    """Tests for error models and exceptions."""
    
    def test_error_response_model(self):
        """Test ErrorResponse model creation."""
        error = ErrorResponse(
            error="test_error",
            message="Test error message",
            details={"key": "value"}
        )
        
        assert error.error == "test_error"
        assert error.message == "Test error message"
        assert error.details == {"key": "value"}
        assert error.request_id is not None
        assert error.timestamp is not None
    
    def test_validation_error_detail(self):
        """Test ValidationErrorDetail model."""
        detail = ValidationErrorDetail(
            field="test_field",
            message="Invalid value",
            invalid_value="bad_value"
        )
        
        assert detail.field == "test_field"
        assert detail.message == "Invalid value"
        assert detail.invalid_value == "bad_value"
    
    def test_validation_error_response(self):
        """Test ValidationErrorResponse model."""
        detail = ValidationErrorDetail(
            field="test_field",
            message="Invalid value"
        )
        
        error = ValidationErrorResponse(
            message="Validation failed",
            validation_errors=[detail]
        )
        
        assert error.error == "validation_error"
        assert len(error.validation_errors) == 1
        assert error.validation_errors[0].field == "test_field"
    
    def test_nasa_mcp_error_exception(self):
        """Test NASAMCPError exception."""
        error = NASAAPIError(
            message="Test error",
            details={"key": "value"},
            error_code="test_error"
        )
        
        assert str(error) == "Test error"
        assert error.details == {"key": "value"}
        assert error.error_code == "test_error"
        
        # Test conversion to ErrorResponse
        response = error.to_error_response()
        assert isinstance(response, ErrorResponse)
        assert response.error == "test_error"
        assert response.message == "Test error"
    
    def test_nasa_api_rate_limited_exception(self):
        """Test NASAAPIRateLimited exception."""
        error = NASAAPIRateLimited(
            message="Rate limited",
            retry_after=60
        )
        
        assert error.retry_after == 60
        assert error.error_code == "nasa_api_rate_limited"
        assert "retry_after" in error.details
    
    def test_nasa_api_invalid_request_exception(self):
        """Test NASAAPIInvalidRequest exception."""
        invalid_params = {"date": "invalid format"}
        error = NASAAPIInvalidRequest(
            message="Invalid parameters",
            invalid_params=invalid_params
        )
        
        assert error.invalid_params == invalid_params
        assert error.error_code == "nasa_api_invalid_request"
        assert "invalid_params" in error.details
    
    def test_configuration_error_exception(self):
        """Test ConfigurationError exception."""
        error = ConfigurationError(
            message="Invalid config",
            config_field="api_key"
        )
        
        assert error.config_field == "api_key"
        assert error.error_code == "configuration_error"
        assert "config_field" in error.details