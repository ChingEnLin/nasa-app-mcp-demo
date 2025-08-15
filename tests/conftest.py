"""
Pytest configuration and shared fixtures.

This module provides shared test configuration, fixtures, and utilities
for all test modules in the test suite.
"""

import asyncio
import os
import sys
from typing import Generator, AsyncGenerator
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add the project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nasa_mcp_demo.main import app
from nasa_mcp_demo.models.config import AppConfig, NASAConfig, CacheConfig, LoggingConfig
from nasa_mcp_demo.services.nasa_service import NASAService


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config() -> AppConfig:
    """Create test configuration."""
    return AppConfig(
        app_name="NASA MCP Demo Test",
        debug=True,
        nasa=NASAConfig(
            api_key="TEST_KEY",
            base_url="https://api.nasa.gov",
            timeout=10,
            max_retries=1,
            rate_limit_per_hour=1000
        ),
        cache=CacheConfig(
            enable_caching=True,
            apod_cache_ttl=60,
            mars_photos_cache_ttl=60,
            neo_cache_ttl=60,
            max_cache_size=10
        ),
        logging=LoggingConfig(
            level="DEBUG",
            format="json",
            enable_request_logging=False,  # Disable for tests
            enable_nasa_api_logging=False
        )
    )


@pytest.fixture
def mock_nasa_client():
    """Create a mock NASA client."""
    client = AsyncMock()
    
    # Set up default return values
    client.get_apod.return_value = AsyncMock()
    client.get_mars_rover_photos.return_value = AsyncMock()
    client.get_neo_data.return_value = AsyncMock()
    client.health_check.return_value = True
    client.close.return_value = None
    
    return client


@pytest.fixture
def mock_nasa_service():
    """Create a mock NASA service with proper return values."""
    service = AsyncMock()
    
    # Import required classes
    from nasa_mcp_demo.services.nasa_service import ProcessedAPOD, ProcessedMarsPhotos, ProcessedNEOData
    from nasa_mcp_demo.models.nasa_responses import APODResponse, MarsRoverResponse, NEOResponse
    from tests.fixtures.nasa_api_responses import MockNASAResponses
    
    # Create proper mock data
    def create_mock_apod(*args, **kwargs):
        mock_apod_data = MockNASAResponses.get_apod_response()
        mock_apod_response = APODResponse(**mock_apod_data)
        return ProcessedAPOD(mock_apod_response)
    
    def create_mock_mars(*args, **kwargs):
        mock_mars_data = MockNASAResponses.get_mars_rover_response()
        mock_mars_response = MarsRoverResponse(**mock_mars_data)
        return ProcessedMarsPhotos(mock_mars_response)
    
    def create_mock_neo(*args, **kwargs):
        mock_neo_data = MockNASAResponses.get_neo_response("2023-12-01", "2023-12-01")
        mock_neo_response = NEOResponse(**mock_neo_data)
        return ProcessedNEOData(mock_neo_response)
    
    # Set up service methods to return proper objects
    service.get_daily_astronomy_picture.return_value = create_mock_apod()
    service.search_mars_photos.return_value = create_mock_mars()
    service.get_near_earth_objects.return_value = create_mock_neo()
    
    # Mock health check
    service.health_check.return_value = {
        "service": "healthy",
        "nasa_api": "healthy",
        "cache": "enabled",
        "timestamp": "2023-12-01T12:00:00Z"
    }
    
    return service


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_test_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    from httpx import AsyncClient
    async with AsyncClient(base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
def clean_dependency_overrides():
    """Automatically clean up dependency overrides after each test."""
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    logger = Mock()
    logger.info = Mock()
    logger.error = Mock()
    logger.warning = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def sample_dates():
    """Provide sample dates for testing."""
    from datetime import date, timedelta
    
    today = date.today()
    return {
        "today": today.strftime('%Y-%m-%d'),
        "yesterday": (today - timedelta(days=1)).strftime('%Y-%m-%d'),
        "last_week": (today - timedelta(days=7)).strftime('%Y-%m-%d'),
        "last_month": (today - timedelta(days=30)).strftime('%Y-%m-%d'),
        "future": (today + timedelta(days=1)).strftime('%Y-%m-%d'),
        "apod_start": "1995-06-16",  # First APOD date
        "before_apod": "1995-06-15"  # Before APOD started
    }


@pytest.fixture
def performance_threshold():
    """Define performance thresholds for testing."""
    return {
        "fast_response": 0.1,      # 100ms
        "normal_response": 0.5,    # 500ms
        "slow_response": 2.0,      # 2 seconds
        "timeout": 30.0            # 30 seconds
    }


# Pytest markers for test categorization
pytest_plugins = []

# Custom markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests that test individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that test component interactions"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take a long time to run"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and load tests"
    )
    config.addinivalue_line(
        "markers", "error_handling: Error handling and edge case tests"
    )


# Test collection customization
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add markers based on test name patterns
        if "performance" in item.name.lower() or "concurrent" in item.name.lower():
            item.add_marker(pytest.mark.performance)
        
        if "error" in item.name.lower() or "fail" in item.name.lower():
            item.add_marker(pytest.mark.error_handling)
        
        if "slow" in item.name.lower() or "sustained" in item.name.lower():
            item.add_marker(pytest.mark.slow)


# Test environment setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables and configuration."""
    # Set test environment variables
    os.environ["TESTING"] = "true"
    os.environ["NASA_API_KEY"] = "TEST_KEY"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    yield
    
    # Clean up after tests
    test_vars = ["TESTING", "NASA_API_KEY", "LOG_LEVEL"]
    for var in test_vars:
        if var in os.environ:
            del os.environ[var]


# Async test utilities
class AsyncTestUtils:
    """Utilities for async testing."""
    
    @staticmethod
    async def wait_for_condition(condition_func, timeout=5.0, interval=0.1):
        """Wait for a condition to become true."""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await condition_func():
                return True
            await asyncio.sleep(interval)
        
        return False
    
    @staticmethod
    async def run_with_timeout(coro, timeout=5.0):
        """Run a coroutine with a timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            pytest.fail(f"Operation timed out after {timeout} seconds")


@pytest.fixture
def async_utils():
    """Provide async test utilities."""
    return AsyncTestUtils()


# Mock data helpers
class MockDataHelper:
    """Helper class for creating mock test data."""
    
    @staticmethod
    def create_mock_response(status_code=200, json_data=None, headers=None):
        """Create a mock HTTP response."""
        from unittest.mock import Mock
        
        response = Mock()
        response.status_code = status_code
        response.json.return_value = json_data or {}
        response.headers = headers or {}
        response.text = str(json_data) if json_data else ""
        
        return response
    
    @staticmethod
    def create_error_response(status_code, message="Test error"):
        """Create a mock error response."""
        return MockDataHelper.create_mock_response(
            status_code=status_code,
            json_data={"error": {"message": message}}
        )


@pytest.fixture
def mock_data_helper():
    """Provide mock data helper."""
    return MockDataHelper()


# Test database/cache cleanup
@pytest.fixture(autouse=True)
def cleanup_cache():
    """Clean up any cache state between tests."""
    # This would clean up any persistent cache state
    # Implementation depends on actual caching mechanism
    yield
    # Cleanup code here if needed


# Performance monitoring for tests
@pytest.fixture
def performance_monitor():
    """Monitor test performance."""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.measurements = []
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self, operation_name="test"):
            if self.start_time:
                duration = time.time() - self.start_time
                self.measurements.append((operation_name, duration))
                self.start_time = None
                return duration
            return 0
        
        def get_measurements(self):
            return self.measurements.copy()
    
    return PerformanceMonitor()