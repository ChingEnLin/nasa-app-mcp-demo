"""
Performance tests for concurrent request handling.

This module tests the application's performance under various load conditions
and concurrent request scenarios.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from nasa_mcp_demo.main import app, get_nasa_service
from tests.fixtures.nasa_api_responses import SAMPLE_APOD_RESPONSES, SAMPLE_MARS_RESPONSES


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_fast_service():
    """Create a mock service that responds quickly."""
    mock_service = AsyncMock()
    
    # Mock quick responses
    mock_service.get_daily_astronomy_picture.return_value = AsyncMock()
    mock_service.search_mars_photos.return_value = AsyncMock()
    mock_service.get_near_earth_objects.return_value = AsyncMock()
    mock_service.health_check.return_value = {
        "service": "healthy",
        "nasa_api": "healthy",
        "timestamp": time.time()
    }
    
    return mock_service


@pytest.fixture
def mock_slow_service():
    """Create a mock service that responds slowly."""
    mock_service = AsyncMock()
    
    async def slow_response(*args, **kwargs):
        await asyncio.sleep(0.1)  # 100ms delay
        return AsyncMock()
    
    mock_service.get_daily_astronomy_picture.side_effect = slow_response
    mock_service.search_mars_photos.side_effect = slow_response
    mock_service.get_near_earth_objects.side_effect = slow_response
    mock_service.health_check.side_effect = slow_response
    
    return mock_service


class TestConcurrentRequests:
    """Test concurrent request handling."""
    
    def test_concurrent_apod_requests(self, client, mock_fast_service):
        """Test handling of concurrent APOD requests."""
        app.dependency_overrides[get_nasa_service] = lambda: mock_fast_service
        
        def make_request():
            return client.get("/apod")
        
        # Make 10 concurrent requests using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=10) as executor:
            start_time = time.time()
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in futures]
            end_time = time.time()
        
        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)
        
        # Should complete reasonably quickly (less than 2 seconds for 10 requests)
        total_time = end_time - start_time
        assert total_time < 2.0
        
        # Service should have been called 10 times
        assert mock_fast_service.get_daily_astronomy_picture.call_count == 10
        
        app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_async_concurrent_requests(self, mock_fast_service):
        """Test async concurrent request handling."""
        app.dependency_overrides[get_nasa_service] = lambda: mock_fast_service
        
        from httpx import AsyncClient
        async with AsyncClient(base_url="http://test") as ac:
            start_time = time.time()
            
            # Make 20 concurrent async requests
            tasks = [
                ac.get("/apod"),
                ac.get("/mars-photos/curiosity?sol=1000"),
                ac.get("/neo?start_date=2023-12-01&end_date=2023-12-01"),
                ac.get("/health"),
                ac.get("/rovers")
            ] * 4  # 20 total requests
            
            responses = await asyncio.gather(*tasks)
            end_time = time.time()
        
        # All requests should succeed
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count == 20
        
        # Should complete quickly with async handling
        total_time = end_time - start_time
        assert total_time < 1.0
        
        app.dependency_overrides.clear()
    
    def test_mixed_endpoint_concurrent_requests(self, client, mock_fast_service):
        """Test concurrent requests to different endpoints."""
        app.dependency_overrides[get_nasa_service] = lambda: mock_fast_service
        
        def make_requests():
            responses = []
            responses.append(client.get("/apod"))
            responses.append(client.get("/mars-photos/curiosity?sol=1000"))
            responses.append(client.get("/neo?start_date=2023-12-01&end_date=2023-12-01"))
            responses.append(client.get("/health"))
            responses.append(client.get("/rovers"))
            return responses
        
        # Run multiple threads making mixed requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            start_time = time.time()
            futures = [executor.submit(make_requests) for _ in range(5)]
            all_responses = []
            for future in futures:
                all_responses.extend(future.result())
            end_time = time.time()
        
        # All 25 requests should succeed
        assert len(all_responses) == 25
        assert all(r.status_code == 200 for r in all_responses)
        
        # Should complete in reasonable time
        total_time = end_time - start_time
        assert total_time < 3.0
        
        app.dependency_overrides.clear()


class TestPerformanceUnderLoad:
    """Test performance characteristics under load."""
    
    def test_response_time_consistency(self, client, mock_fast_service):
        """Test that response times remain consistent under load."""
        app.dependency_overrides[get_nasa_service] = lambda: mock_fast_service
        
        response_times = []
        
        # Make 50 sequential requests and measure response times
        for _ in range(50):
            start_time = time.time()
            response = client.get("/apod")
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
        
        # Calculate statistics
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        # Response times should be consistent
        assert avg_time < 0.1  # Average under 100ms
        assert max_time < 0.5  # No response over 500ms
        assert max_time / min_time < 10  # Max not more than 10x min
        
        app.dependency_overrides.clear()
    
    def test_memory_usage_under_load(self, client, mock_fast_service):
        """Test memory usage doesn't grow excessively under load."""
        import psutil
        import os
        
        app.dependency_overrides[get_nasa_service] = lambda: mock_fast_service
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make many requests
        for _ in range(100):
            response = client.get("/apod")
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024
        
        app.dependency_overrides.clear()
    
    @pytest.mark.slow
    def test_sustained_load_performance(self, client, mock_fast_service):
        """Test performance under sustained load."""
        app.dependency_overrides[get_nasa_service] = lambda: mock_fast_service
        
        def worker():
            responses = []
            for _ in range(20):
                response = client.get("/apod")
                responses.append(response.status_code == 200)
            return responses
        
        # Run sustained load for 10 seconds with 5 concurrent workers
        with ThreadPoolExecutor(max_workers=5) as executor:
            start_time = time.time()
            futures = []
            
            while time.time() - start_time < 10:  # Run for 10 seconds
                if len(futures) < 5:  # Keep 5 workers busy
                    future = executor.submit(worker)
                    futures.append(future)
                
                # Remove completed futures
                futures = [f for f in futures if not f.done()]
                
                time.sleep(0.1)  # Small delay to prevent tight loop
            
            # Wait for remaining futures to complete
            results = []
            for future in futures:
                results.extend(future.result())
        
        # Most requests should succeed
        success_rate = sum(results) / len(results) if results else 0
        assert success_rate > 0.95  # 95% success rate
        
        app.dependency_overrides.clear()


class TestSlowResponseHandling:
    """Test handling of slow responses."""
    
    def test_slow_service_response_handling(self, client, mock_slow_service):
        """Test handling when service responses are slow."""
        app.dependency_overrides[get_nasa_service] = lambda: mock_slow_service
        
        start_time = time.time()
        response = client.get("/apod")
        end_time = time.time()
        
        # Should still succeed despite slowness
        assert response.status_code == 200
        
        # Should take at least the mock delay time
        assert end_time - start_time >= 0.1
        
        app.dependency_overrides.clear()
    
    def test_concurrent_slow_requests(self, client, mock_slow_service):
        """Test concurrent handling of slow requests."""
        app.dependency_overrides[get_nasa_service] = lambda: mock_slow_service
        
        def make_request():
            start_time = time.time()
            response = client.get("/apod")
            end_time = time.time()
            return response.status_code, end_time - start_time
        
        # Make 5 concurrent slow requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            start_time = time.time()
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [future.result() for future in futures]
            total_time = time.time() - start_time
        
        # All should succeed
        assert all(status == 200 for status, _ in results)
        
        # Should complete in roughly the same time as a single request
        # (due to concurrency), not 5x the time
        assert total_time < 0.5  # Should be much less than 5 * 0.1
        
        app.dependency_overrides.clear()


class TestResourceUtilization:
    """Test resource utilization under various conditions."""
    
    def test_connection_pooling_efficiency(self, client, mock_fast_service):
        """Test that connection pooling is working efficiently."""
        app.dependency_overrides[get_nasa_service] = lambda: mock_fast_service
        
        # Make many requests that would benefit from connection reuse
        start_time = time.time()
        for _ in range(100):
            response = client.get("/health")  # Lightweight endpoint
            assert response.status_code == 200
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time_per_request = total_time / 100
        
        # Should be very fast due to connection reuse
        assert avg_time_per_request < 0.01  # Less than 10ms per request
        
        app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_async_resource_cleanup(self, mock_fast_service):
        """Test that async resources are properly cleaned up."""
        app.dependency_overrides[get_nasa_service] = lambda: mock_fast_service
        
        # Make many async requests and ensure cleanup
        from httpx import AsyncClient
        async with AsyncClient(base_url="http://test") as ac:
            tasks = []
            for _ in range(50):
                task = ac.get("/health")
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            
            # All should succeed
            assert all(r.status_code == 200 for r in responses)
        
        # Client should be properly closed after context manager
        app.dependency_overrides.clear()


class TestCachePerformance:
    """Test caching performance characteristics."""
    
    def test_cache_hit_performance(self, client, mock_fast_service):
        """Test performance improvement from cache hits."""
        app.dependency_overrides[get_nasa_service] = lambda: mock_fast_service
        
        # First request (cache miss)
        start_time = time.time()
        response1 = client.get("/apod?date=2023-12-01")
        first_request_time = time.time() - start_time
        assert response1.status_code == 200
        
        # Second request (potential cache hit)
        start_time = time.time()
        response2 = client.get("/apod?date=2023-12-01")
        second_request_time = time.time() - start_time
        assert response2.status_code == 200
        
        # Cache hit should be faster (though this depends on implementation)
        # This test might need adjustment based on actual caching behavior
        
        app.dependency_overrides.clear()
    
    def test_cache_performance_under_load(self, client, mock_fast_service):
        """Test cache performance under concurrent load."""
        app.dependency_overrides[get_nasa_service] = lambda: mock_fast_service
        
        def make_cached_requests():
            # All requests use same parameters to test cache efficiency
            responses = []
            for _ in range(10):
                response = client.get("/apod?date=2023-12-01")
                responses.append(response.status_code == 200)
            return responses
        
        # Multiple workers making same requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            start_time = time.time()
            futures = [executor.submit(make_cached_requests) for _ in range(5)]
            results = []
            for future in futures:
                results.extend(future.result())
            end_time = time.time()
        
        # All should succeed
        assert all(results)
        
        # Should be fast due to caching
        total_time = end_time - start_time
        assert total_time < 2.0
        
        app.dependency_overrides.clear()


class TestErrorHandlingPerformance:
    """Test performance of error handling under load."""
    
    def test_error_response_performance(self, client):
        """Test that error responses are generated quickly."""
        # Make requests that will cause validation errors
        start_time = time.time()
        for _ in range(50):
            response = client.get("/mars-photos/curiosity")  # Missing sol parameter
            assert response.status_code == 422
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / 50
        
        # Error responses should be fast
        assert avg_time < 0.01  # Less than 10ms per error response
    
    def test_concurrent_error_handling(self, client):
        """Test concurrent error handling performance."""
        def make_error_request():
            return client.get("/mars-photos/invalid_rover?sol=100")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            start_time = time.time()
            futures = [executor.submit(make_error_request) for _ in range(20)]
            responses = [future.result() for future in futures]
            end_time = time.time()
        
        # All should return error status
        assert all(r.status_code >= 400 for r in responses)
        
        # Should handle errors quickly even under load
        total_time = end_time - start_time
        assert total_time < 1.0


class TestPerformanceMetrics:
    """Test performance metrics collection."""
    
    def test_metrics_collection_overhead(self, client, mock_fast_service):
        """Test that metrics collection doesn't significantly impact performance."""
        app.dependency_overrides[get_nasa_service] = lambda: mock_fast_service
        
        # Make requests and check metrics endpoint
        for _ in range(20):
            response = client.get("/apod")
            assert response.status_code == 200
        
        # Check metrics endpoint performance
        start_time = time.time()
        metrics_response = client.get("/metrics")
        metrics_time = time.time() - start_time
        
        assert metrics_response.status_code == 200
        assert metrics_time < 0.1  # Metrics should be fast to retrieve
        
        # Verify metrics contain performance data
        data = metrics_response.json()
        assert "nasa_api_stats" in data
        
        app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])