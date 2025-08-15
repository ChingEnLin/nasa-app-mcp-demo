"""
NASA API client with comprehensive error handling and retry logic.

This module provides an async HTTP client for interacting with NASA's public APIs,
including APOD, Mars Rover Photos, and Near Earth Objects. It includes proper
timeout handling, exponential backoff retry logic, rate limiting compliance,
and comprehensive error handling.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from urllib.parse import urljoin

import httpx
from httpx import AsyncClient, Response, TimeoutException, HTTPStatusError
import structlog

from ..models.config import NASAConfig
from ..models.errors import (
    NASAAPIError,
    NASAAPIUnavailable,
    NASAAPIRateLimited,
    NASAAPIInvalidRequest,
    NASAAPITimeout,
)
from ..models.nasa_responses import APODResponse, MarsRoverResponse, NEOResponse
from ..logging_config import NASAAPILogger, PerformanceMonitor, ErrorTracker


logger = structlog.get_logger(__name__)


class RateLimiter:
    """Simple rate limiter for NASA API requests."""
    
    def __init__(self, max_requests: int, time_window: int = 3600):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds (default: 1 hour)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: list[datetime] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire permission to make a request, blocking if necessary."""
        async with self._lock:
            now = datetime.now()
            
            # Remove old requests outside the time window
            cutoff = now - timedelta(seconds=self.time_window)
            self.requests = [req_time for req_time in self.requests if req_time > cutoff]
            
            # Check if we can make a request
            if len(self.requests) >= self.max_requests:
                # Calculate wait time until oldest request expires
                oldest_request = min(self.requests)
                wait_time = (oldest_request + timedelta(seconds=self.time_window) - now).total_seconds()
                
                if wait_time > 0:
                    logger.warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                    # Recursively try again after waiting
                    await self.acquire()
                    return
            
            # Record this request
            self.requests.append(now)


class NASAClient:
    """
    Async HTTP client for NASA APIs with comprehensive error handling.
    
    Features:
    - Automatic retry with exponential backoff
    - Rate limiting compliance
    - Comprehensive error handling
    - Request/response logging
    - Timeout handling
    - Performance monitoring
    """
    
    def __init__(self, config: NASAConfig):
        """
        Initialize NASA API client.
        
        Args:
            config: NASA API configuration
        """
        self.config = config
        self.base_url = str(config.base_url)
        self.api_key = config.api_key
        
        # Initialize logging and monitoring utilities
        self.api_logger = NASAAPILogger(logger)
        self.performance_monitor = PerformanceMonitor(logger)
        self.error_tracker = ErrorTracker(logger)
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            max_requests=config.rate_limit_per_hour,
            time_window=3600
        )
        
        # HTTP client configuration
        self.client_config = {
            "timeout": httpx.Timeout(config.timeout),
            "limits": httpx.Limits(max_keepalive_connections=10, max_connections=20),
            "headers": {
                "User-Agent": "NASA-MCP-Demo/1.0.0",
                "Accept": "application/json",
            }
        }
        
        self._client: Optional[AsyncClient] = None
        
        # Performance tracking
        self.request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "rate_limit_hits": 0,
            "total_response_time_ms": 0.0
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_client(self) -> AsyncClient:
        """Ensure HTTP client is initialized."""
        if self._client is None or self._client.is_closed:
            self._client = AsyncClient(**self.client_config)
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and error handling.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            max_retries: Maximum retry attempts (uses config default if None)
        
        Returns:
            JSON response data
        
        Raises:
            NASAAPIError: For various API-related errors
        """
        if max_retries is None:
            max_retries = self.config.max_retries
        
        # Prepare request parameters
        request_params = {"api_key": self.api_key}
        if params:
            request_params.update(params)
        
        url = urljoin(self.base_url, endpoint)
        
        # Start performance monitoring
        start_time = time.time()
        
        # Log request start
        self.api_logger.log_request(endpoint, params)
        
        # Update request statistics
        self.request_stats["total_requests"] += 1
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        client = await self._ensure_client()
        
        for attempt in range(max_retries + 1):
            try:
                # Log retry attempt if not first attempt
                if attempt > 0:
                    logger.info(
                        "Retrying NASA API request",
                        endpoint=endpoint,
                        attempt=attempt + 1,
                        max_retries=max_retries + 1
                    )
                
                response = await client.get(url, params=request_params)
                
                # Calculate response time
                response_time_ms = (time.time() - start_time) * 1000
                
                # Calculate response size safely
                response_size = 0
                try:
                    if hasattr(response, 'content') and response.content:
                        response_size = len(response.content)
                except (TypeError, AttributeError):
                    # Handle mock objects or other issues
                    response_size = 0
                
                # Log response
                self.api_logger.log_response(
                    endpoint,
                    response.status_code,
                    response_size,
                    response_time_ms
                )
                
                # Handle different HTTP status codes
                if response.status_code == 200:
                    data = response.json()
                    
                    # Update success statistics
                    self.request_stats["successful_requests"] += 1
                    self.request_stats["total_response_time_ms"] += response_time_ms
                    
                    # Log successful completion
                    logger.info(
                        "NASA API request successful",
                        endpoint=endpoint,
                        response_time_ms=round(response_time_ms, 2),
                        response_size_bytes=response_size,
                        attempt=attempt + 1
                    )
                    
                    return data
                
                elif response.status_code == 429:
                    # Rate limited
                    retry_after = int(response.headers.get("Retry-After", 60))
                    self.request_stats["rate_limit_hits"] += 1
                    
                    # Log rate limiting
                    self.api_logger.log_rate_limit(endpoint, retry_after)
                    
                    raise NASAAPIRateLimited(
                        message=f"Rate limit exceeded. Retry after {retry_after} seconds",
                        status_code=response.status_code,
                        retry_after=retry_after,
                        response_data=self._safe_json_parse(response)
                    )
                
                elif response.status_code == 400:
                    # Bad request
                    error_data = self._safe_json_parse(response)
                    error_message = error_data.get('error', {}).get('message', 'Unknown error')
                    
                    # Log validation error
                    self.api_logger.log_error(
                        endpoint,
                        NASAAPIInvalidRequest(error_message),
                        retry_attempt=attempt
                    )
                    
                    raise NASAAPIInvalidRequest(
                        message=f"Invalid request parameters: {error_message}",
                        status_code=response.status_code,
                        response_data=error_data
                    )
                
                elif response.status_code == 403:
                    # Forbidden (usually API key issues)
                    error_data = self._safe_json_parse(response)
                    error_message = error_data.get('error', {}).get('message', 'Forbidden')
                    
                    # Log authentication error
                    self.api_logger.log_error(
                        endpoint,
                        NASAAPIInvalidRequest(error_message),
                        retry_attempt=attempt
                    )
                    
                    raise NASAAPIInvalidRequest(
                        message=f"API key invalid or insufficient permissions: {error_message}",
                        status_code=response.status_code,
                        response_data=error_data
                    )
                
                elif response.status_code >= 500:
                    # Server error - retry
                    error_data = self._safe_json_parse(response)
                    error_message = f"NASA API server error: {response.status_code}"
                    
                    if attempt < max_retries:
                        wait_time = self._calculate_backoff_time(attempt)
                        
                        # Log retry attempt
                        logger.warning(
                            "NASA API server error, retrying",
                            endpoint=endpoint,
                            status_code=response.status_code,
                            attempt=attempt + 1,
                            wait_time_seconds=wait_time
                        )
                        
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # Log final failure
                        self.api_logger.log_error(
                            endpoint,
                            NASAAPIUnavailable(error_message),
                            retry_attempt=attempt
                        )
                        
                        raise NASAAPIUnavailable(
                            message=error_message,
                            status_code=response.status_code,
                            response_data=error_data
                        )
                
                else:
                    # Other HTTP errors
                    error_data = self._safe_json_parse(response)
                    error_message = f"Unexpected HTTP status: {response.status_code}"
                    
                    # Log unexpected error
                    self.api_logger.log_error(
                        endpoint,
                        NASAAPIError(error_message),
                        retry_attempt=attempt
                    )
                    
                    raise NASAAPIError(
                        message=error_message,
                        status_code=response.status_code,
                        response_data=error_data
                    )
            
            except TimeoutException as e:
                # Log timeout error
                self.api_logger.log_error(
                    endpoint,
                    NASAAPITimeout(f"Request timeout after {self.config.timeout}s"),
                    retry_attempt=attempt
                )
                
                if attempt < max_retries:
                    wait_time = self._calculate_backoff_time(attempt)
                    logger.warning(
                        "NASA API request timeout, retrying",
                        endpoint=endpoint,
                        timeout_seconds=self.config.timeout,
                        attempt=attempt + 1,
                        wait_time_seconds=wait_time
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Update failure statistics
                    self.request_stats["failed_requests"] += 1
                    
                    raise NASAAPITimeout(
                        message=f"Request timed out after {self.config.timeout} seconds",
                        timeout_duration=self.config.timeout
                    ) from e
            
            except HTTPStatusError as e:
                # This shouldn't happen as we handle status codes above,
                # but included for completeness
                self.api_logger.log_error(
                    endpoint,
                    NASAAPIError(f"HTTP error: {e}"),
                    retry_attempt=attempt
                )
                
                # Update failure statistics
                self.request_stats["failed_requests"] += 1
                
                raise NASAAPIError(
                    message=f"HTTP error: {e}",
                    status_code=e.response.status_code if e.response else None
                ) from e
            
            except NASAAPIError:
                # Re-raise NASA API errors without retrying
                # Update failure statistics
                self.request_stats["failed_requests"] += 1
                raise
            
            except Exception as e:
                # Log unexpected error
                self.api_logger.log_error(
                    endpoint,
                    e,
                    retry_attempt=attempt
                )
                
                if attempt < max_retries:
                    wait_time = self._calculate_backoff_time(attempt)
                    logger.warning(
                        "Unexpected error during NASA API request, retrying",
                        endpoint=endpoint,
                        error=str(e),
                        error_type=type(e).__name__,
                        attempt=attempt + 1,
                        wait_time_seconds=wait_time
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Update failure statistics
                    self.request_stats["failed_requests"] += 1
                    
                    # Track error for debugging
                    self.error_tracker.track_error(
                        e,
                        context="nasa_api_request",
                        endpoint=endpoint,
                        attempt=attempt + 1
                    )
                    
                    raise NASAAPIError(
                        message=f"Unexpected error during API request: {e}"
                    ) from e
        
        # This should never be reached, but included for type safety
        # Update failure statistics
        self.request_stats["failed_requests"] += 1
        raise NASAAPIError("Maximum retries exceeded")
    
    def _calculate_backoff_time(self, attempt: int) -> float:
        """Calculate exponential backoff time."""
        base_delay = self.config.retry_backoff_factor
        return min(base_delay * (2 ** attempt), 60.0)  # Cap at 60 seconds
    
    def _safe_json_parse(self, response: Response) -> Dict[str, Any]:
        """Safely parse JSON response, returning empty dict on failure."""
        try:
            return response.json()
        except Exception:
            return {"error": {"message": "Failed to parse response JSON"}}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        stats = self.request_stats.copy()
        
        # Calculate derived metrics
        if stats["total_requests"] > 0:
            stats["success_rate"] = (
                stats["successful_requests"] / stats["total_requests"] * 100
            )
            stats["failure_rate"] = (
                stats["failed_requests"] / stats["total_requests"] * 100
            )
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0
        
        if stats["successful_requests"] > 0:
            stats["avg_response_time_ms"] = (
                stats["total_response_time_ms"] / stats["successful_requests"]
            )
        else:
            stats["avg_response_time_ms"] = 0.0
        
        return stats
    
    def reset_performance_stats(self) -> None:
        """Reset performance statistics."""
        self.request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "rate_limit_hits": 0,
            "total_response_time_ms": 0.0
        }
        
        logger.info("NASA API client performance statistics reset")
    
    def _safe_json_parse(self, response: Response) -> Dict[str, Any]:
        """Safely parse JSON response, returning empty dict on failure."""
        try:
            return response.json()
        except Exception:
            return {"error": {"message": response.text or "Unknown error"}}
    
    async def get_apod(self, date: Optional[str] = None) -> APODResponse:
        """
        Get Astronomy Picture of the Day.
        
        Args:
            date: Date in YYYY-MM-DD format (optional, defaults to today)
        
        Returns:
            APOD response data
        
        Raises:
            NASAAPIError: For API-related errors
        """
        params = {}
        if date:
            params["date"] = date
        
        try:
            data = await self._make_request("/planetary/apod", params)
            return APODResponse(**data)
        except Exception as e:
            if isinstance(e, NASAAPIError):
                raise
            raise NASAAPIError(f"Failed to parse APOD response: {e}") from e
    
    async def get_mars_rover_photos(
        self,
        rover: str,
        sol: int,
        camera: Optional[str] = None
    ) -> MarsRoverResponse:
        """
        Get Mars rover photos.
        
        Args:
            rover: Rover name (curiosity, opportunity, spirit, perseverance)
            sol: Martian sol (day) number
            camera: Camera name (optional)
        
        Returns:
            Mars rover photos response data
        
        Raises:
            NASAAPIError: For API-related errors
        """
        params = {"sol": str(sol)}
        if camera:
            params["camera"] = camera
        
        try:
            data = await self._make_request(f"/mars-photos/api/v1/rovers/{rover}/photos", params)
            
            # Transform the response to match our model
            photos = []
            for photo in data.get("photos", []):
                photos.append({
                    "id": photo["id"],
                    "img_src": photo["img_src"],
                    "earth_date": photo["earth_date"],
                    "rover_name": photo["rover"]["name"].lower(),
                    "camera_name": photo["camera"]["name"],
                    "camera_full_name": photo["camera"]["full_name"]
                })
            
            response_data = {
                "photos": photos,
                "rover": rover.lower(),
                "sol": sol,
                "total_photos": len(photos)
            }
            
            return MarsRoverResponse(**response_data)
        except Exception as e:
            if isinstance(e, NASAAPIError):
                raise
            raise NASAAPIError(f"Failed to parse Mars rover photos response: {e}") from e
    
    async def get_neo_data(self, start_date: str, end_date: str) -> NEOResponse:
        """
        Get Near Earth Objects data.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            NEO response data
        
        Raises:
            NASAAPIError: For API-related errors
        """
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        try:
            data = await self._make_request("/neo/rest/v1/feed", params)
            
            # Transform the response to match our model
            neo_objects = {}
            for date_key, objects in data.get("near_earth_objects", {}).items():
                neo_objects[date_key] = []
                for obj in objects:
                    # Get the first close approach data
                    close_approach = obj["close_approach_data"][0] if obj.get("close_approach_data") else {}
                    
                    neo_objects[date_key].append({
                        "id": obj["id"],
                        "name": obj["name"],
                        "estimated_diameter_km": obj["estimated_diameter"]["kilometers"],
                        "is_potentially_hazardous": obj["is_potentially_hazardous_asteroid"],
                        "close_approach_date": close_approach.get("close_approach_date", start_date),
                        "miss_distance_km": float(close_approach.get("miss_distance", {}).get("kilometers", 0)),
                        "relative_velocity_kmh": float(close_approach.get("relative_velocity", {}).get("kilometers_per_hour", 0))
                    })
            
            response_data = {
                "near_earth_objects": neo_objects,
                "element_count": data.get("element_count", 0),
                "date_range": {
                    "start_date": start_date,
                    "end_date": end_date
                }
            }
            
            return NEOResponse(**response_data)
        except Exception as e:
            if isinstance(e, NASAAPIError):
                raise
            raise NASAAPIError(f"Failed to parse NEO response: {e}") from e
    
    async def health_check(self) -> bool:
        """
        Check if NASA API is available.
        
        Returns:
            True if API is available, False otherwise
        """
        try:
            # Use a simple APOD request as health check
            await self.get_apod()
            return True
        except Exception as e:
            logger.warning(f"NASA API health check failed: {e}")
            return False