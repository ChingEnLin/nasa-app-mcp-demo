"""
NASA service layer with business logic and data transformation.

This module provides the business logic layer for NASA data operations,
including data transformation, enrichment, input validation, and caching.
"""

import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from functools import lru_cache
import hashlib
import json

import structlog

from ..clients.nasa_client import NASAClient
from ..models.config import AppConfig, CacheConfig
from ..models.errors import NASAAPIError, NASAAPIInvalidRequest
from ..models.nasa_responses import APODResponse, MarsRoverResponse, NEOResponse
from ..logging_config import PerformanceMonitor, ErrorTracker


logger = structlog.get_logger(__name__)


class CacheEntry:
    """Simple cache entry with TTL support."""
    
    def __init__(self, data: Any, ttl: int):
        self.data = data
        self.created_at = datetime.now()
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)


class SimpleCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired."""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if entry.is_expired():
            self._remove(key)
            return None
        
        # Update access order for LRU
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        return entry.data
    
    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set item in cache with TTL."""
        # Remove expired entries first
        self._cleanup_expired()
        
        # If at max capacity, remove least recently used
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._remove_lru()
        
        self._cache[key] = CacheEntry(value, ttl)
        
        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def _remove(self, key: str) -> None:
        """Remove item from cache."""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)
    
    def _remove_lru(self) -> None:
        """Remove least recently used item."""
        if self._access_order:
            lru_key = self._access_order[0]
            self._remove(lru_key)
    
    def _cleanup_expired(self) -> None:
        """Remove all expired entries."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            self._remove(key)


class ProcessedAPOD:
    """Processed APOD data with enrichments."""
    
    def __init__(self, apod: APODResponse):
        self.date = apod.date
        self.title = apod.title
        self.explanation = apod.explanation
        self.url = str(apod.url)
        self.media_type = apod.media_type
        self.copyright = apod.copyright
        self.hdurl = str(apod.hdurl) if apod.hdurl else None
        
        # Enrichments
        self.is_image = apod.media_type == "image"
        self.is_video = apod.media_type == "video"
        self.has_hd_version = apod.hdurl is not None
        self.word_count = len(apod.explanation.split())
        self.is_recent = self._is_recent_date(apod.date)
    
    def _is_recent_date(self, date_str: str) -> bool:
        """Check if the APOD date is within the last 30 days."""
        try:
            apod_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            return (date.today() - apod_date).days <= 30
        except ValueError:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "date": self.date,
            "title": self.title,
            "explanation": self.explanation,
            "url": self.url,
            "media_type": self.media_type,
            "copyright": self.copyright,
            "hdurl": self.hdurl,
            "is_image": self.is_image,
            "is_video": self.is_video,
            "has_hd_version": self.has_hd_version,
            "word_count": self.word_count,
            "is_recent": self.is_recent
        }


class ProcessedMarsPhotos:
    """Processed Mars rover photos with enrichments."""
    
    def __init__(self, mars_response: MarsRoverResponse):
        self.rover = mars_response.rover
        self.sol = mars_response.sol
        self.total_photos = mars_response.total_photos
        self.photos = [self._process_photo(photo) for photo in mars_response.photos]
        
        # Enrichments
        self.cameras_used = list(set(photo["camera_name"] for photo in self.photos))
        self.earth_dates = list(set(photo["earth_date"] for photo in self.photos))
        self.has_photos = len(self.photos) > 0
        self.camera_summary = self._create_camera_summary()
    
    def _process_photo(self, photo) -> Dict[str, Any]:
        """Process individual photo with enrichments."""
        return {
            "id": photo.id,
            "img_src": str(photo.img_src),
            "earth_date": photo.earth_date,
            "rover_name": photo.rover_name,
            "camera_name": photo.camera_name,
            "camera_full_name": photo.camera_full_name,
            # Enrichments
            "is_color_camera": self._is_color_camera(photo.camera_name),
            "camera_type": self._get_camera_type(photo.camera_name)
        }
    
    def _is_color_camera(self, camera_name: str) -> bool:
        """Determine if camera captures color images."""
        color_cameras = ["MAST", "MAHLI", "MARDI", "NAVCAM", "FHAZ", "RHAZ"]
        return camera_name.upper() in color_cameras
    
    def _get_camera_type(self, camera_name: str) -> str:
        """Get camera type description."""
        camera_types = {
            "FHAZ": "Front Hazard Avoidance Camera",
            "RHAZ": "Rear Hazard Avoidance Camera",
            "MAST": "Mast Camera",
            "CHEMCAM": "Chemistry and Camera Complex",
            "MAHLI": "Mars Hand Lens Imager",
            "MARDI": "Mars Descent Imager",
            "NAVCAM": "Navigation Camera",
            "PANCAM": "Panoramic Camera",
            "MINITES": "Miniature Thermal Emission Spectrometer"
        }
        return camera_types.get(camera_name.upper(), "Unknown Camera Type")
    
    def _create_camera_summary(self) -> Dict[str, int]:
        """Create summary of photos by camera."""
        summary = {}
        for photo in self.photos:
            camera = photo["camera_name"]
            summary[camera] = summary.get(camera, 0) + 1
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "rover": self.rover,
            "sol": self.sol,
            "total_photos": self.total_photos,
            "photos": self.photos,
            "cameras_used": self.cameras_used,
            "earth_dates": self.earth_dates,
            "has_photos": self.has_photos,
            "camera_summary": self.camera_summary
        }


class ProcessedNEOData:
    """Processed Near Earth Objects data with enrichments."""
    
    def __init__(self, neo_response: NEOResponse):
        self.element_count = neo_response.element_count
        self.date_range = neo_response.date_range
        self.near_earth_objects = self._process_neo_objects(neo_response.near_earth_objects)
        
        # Enrichments
        self.total_objects = sum(len(objects) for objects in self.near_earth_objects.values())
        self.hazardous_count = self._count_hazardous_objects()
        self.size_categories = self._categorize_by_size()
        self.closest_approach = self._find_closest_approach()
        self.fastest_object = self._find_fastest_object()
    
    def _process_neo_objects(self, neo_objects: Dict[str, List]) -> Dict[str, List[Dict[str, Any]]]:
        """Process NEO objects with enrichments."""
        processed = {}
        for date_key, objects in neo_objects.items():
            processed[date_key] = [self._process_neo_object(obj) for obj in objects]
        return processed
    
    def _process_neo_object(self, neo_obj) -> Dict[str, Any]:
        """Process individual NEO object with enrichments."""
        # Calculate average diameter
        diameter_data = neo_obj.estimated_diameter_km
        avg_diameter = (
            diameter_data["estimated_diameter_min"] + 
            diameter_data["estimated_diameter_max"]
        ) / 2
        
        return {
            "id": neo_obj.id,
            "name": neo_obj.name,
            "estimated_diameter_km": diameter_data,
            "average_diameter_km": round(avg_diameter, 3),
            "is_potentially_hazardous": neo_obj.is_potentially_hazardous,
            "close_approach_date": neo_obj.close_approach_date,
            "miss_distance_km": neo_obj.miss_distance_km,
            "relative_velocity_kmh": neo_obj.relative_velocity_kmh,
            # Enrichments
            "size_category": self._categorize_size(avg_diameter),
            "speed_category": self._categorize_speed(neo_obj.relative_velocity_kmh),
            "distance_category": self._categorize_distance(neo_obj.miss_distance_km)
        }
    
    def _categorize_size(self, diameter_km: float) -> str:
        """Categorize NEO by size."""
        if diameter_km < 0.01:
            return "Very Small"
        elif diameter_km < 0.1:
            return "Small"
        elif diameter_km < 1.0:
            return "Medium"
        elif diameter_km < 10.0:
            return "Large"
        else:
            return "Very Large"
    
    def _categorize_speed(self, velocity_kmh: float) -> str:
        """Categorize NEO by relative velocity."""
        if velocity_kmh < 20000:
            return "Slow"
        elif velocity_kmh < 50000:
            return "Moderate"
        elif velocity_kmh < 100000:
            return "Fast"
        else:
            return "Very Fast"
    
    def _categorize_distance(self, distance_km: float) -> str:
        """Categorize NEO by miss distance."""
        lunar_distance = 384400  # km to moon
        if distance_km < lunar_distance:
            return "Closer than Moon"
        elif distance_km < lunar_distance * 5:
            return "Close"
        elif distance_km < lunar_distance * 20:
            return "Moderate"
        else:
            return "Far"
    
    def _count_hazardous_objects(self) -> int:
        """Count potentially hazardous objects."""
        count = 0
        for objects in self.near_earth_objects.values():
            count += sum(1 for obj in objects if obj["is_potentially_hazardous"])
        return count
    
    def _categorize_by_size(self) -> Dict[str, int]:
        """Create size category summary."""
        categories = {}
        for objects in self.near_earth_objects.values():
            for obj in objects:
                category = obj["size_category"]
                categories[category] = categories.get(category, 0) + 1
        return categories
    
    def _find_closest_approach(self) -> Optional[Dict[str, Any]]:
        """Find the object with closest approach."""
        closest = None
        min_distance = float('inf')
        
        for objects in self.near_earth_objects.values():
            for obj in objects:
                if obj["miss_distance_km"] < min_distance:
                    min_distance = obj["miss_distance_km"]
                    closest = obj
        
        return closest
    
    def _find_fastest_object(self) -> Optional[Dict[str, Any]]:
        """Find the fastest moving object."""
        fastest = None
        max_velocity = 0
        
        for objects in self.near_earth_objects.values():
            for obj in objects:
                if obj["relative_velocity_kmh"] > max_velocity:
                    max_velocity = obj["relative_velocity_kmh"]
                    fastest = obj
        
        return fastest
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "element_count": self.element_count,
            "date_range": self.date_range,
            "near_earth_objects": self.near_earth_objects,
            "total_objects": self.total_objects,
            "hazardous_count": self.hazardous_count,
            "size_categories": self.size_categories,
            "closest_approach": self.closest_approach,
            "fastest_object": self.fastest_object
        }


class NASAService:
    """
    NASA service layer providing business logic and data transformation.
    
    This service layer sits between the NASA API client and the application
    endpoints, providing data transformation, enrichment, validation, and caching.
    """
    
    def __init__(self, config: AppConfig, nasa_client: Optional[NASAClient] = None):
        """
        Initialize NASA service.
        
        Args:
            config: Application configuration
            nasa_client: NASA API client (optional, will create if not provided)
        """
        self.config = config
        self.cache_config = config.cache
        self.nasa_client = nasa_client
        
        # Initialize cache if enabled
        if self.cache_config.enable_caching:
            self.cache = SimpleCache(max_size=self.cache_config.max_cache_size)
        else:
            self.cache = None
    
    async def get_nasa_client(self) -> NASAClient:
        """Get or create NASA client."""
        if self.nasa_client is None:
            self.nasa_client = NASAClient(self.config.nasa)
        return self.nasa_client
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters."""
        # Sort kwargs for consistent key generation
        sorted_params = sorted(kwargs.items())
        params_str = json.dumps(sorted_params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        return f"{prefix}:{params_hash}"
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get item from cache if caching is enabled."""
        if self.cache is None:
            return None
        return self.cache.get(key)
    
    def _set_in_cache(self, key: str, value: Any, ttl: int) -> None:
        """Set item in cache if caching is enabled."""
        if self.cache is not None:
            self.cache.set(key, value, ttl)
    
    async def get_daily_astronomy_picture(
        self, 
        date: Optional[str] = None
    ) -> ProcessedAPOD:
        """
        Get Astronomy Picture of the Day with enrichments.
        
        Args:
            date: Date in YYYY-MM-DD format (optional, defaults to today)
        
        Returns:
            Processed APOD data with enrichments
        
        Raises:
            NASAAPIInvalidRequest: For invalid date format or future dates
            NASAAPIError: For API-related errors
        """
        # Validate and sanitize input
        validated_date = self._validate_apod_date(date)
        
        # Check cache first
        cache_key = self._generate_cache_key("apod", date=validated_date)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            logger.debug(f"Returning cached APOD for date: {validated_date}")
            return cached_result
        
        try:
            # Get data from NASA API
            nasa_client = await self.get_nasa_client()
            apod_response = await nasa_client.get_apod(validated_date)
            
            # Process and enrich data
            processed_apod = ProcessedAPOD(apod_response)
            
            # Cache the result
            self._set_in_cache(
                cache_key, 
                processed_apod, 
                self.cache_config.apod_cache_ttl
            )
            
            logger.info(f"Successfully retrieved APOD for date: {validated_date}")
            return processed_apod
            
        except NASAAPIError:
            # Re-raise NASA API errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting APOD: {e}")
            raise NASAAPIError(f"Failed to get astronomy picture: {e}") from e
    
    async def search_mars_photos(
        self,
        rover: str,
        sol: int,
        camera: Optional[str] = None
    ) -> ProcessedMarsPhotos:
        """
        Search Mars rover photos with enrichments.
        
        Args:
            rover: Rover name (curiosity, opportunity, spirit, perseverance)
            sol: Martian sol (day) number
            camera: Camera name (optional)
        
        Returns:
            Processed Mars photos data with enrichments
        
        Raises:
            NASAAPIInvalidRequest: For invalid parameters
            NASAAPIError: For API-related errors
        """
        # Validate and sanitize input
        validated_rover = self._validate_rover_name(rover)
        validated_sol = self._validate_sol(sol)
        validated_camera = self._validate_camera_name(camera) if camera else None
        
        # Check cache first
        cache_key = self._generate_cache_key(
            "mars_photos", 
            rover=validated_rover, 
            sol=validated_sol, 
            camera=validated_camera
        )
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            logger.debug(f"Returning cached Mars photos for {validated_rover} sol {validated_sol}")
            return cached_result
        
        try:
            # Get data from NASA API
            nasa_client = await self.get_nasa_client()
            mars_response = await nasa_client.get_mars_rover_photos(
                validated_rover, validated_sol, validated_camera
            )
            
            # Process and enrich data
            processed_photos = ProcessedMarsPhotos(mars_response)
            
            # Cache the result
            self._set_in_cache(
                cache_key,
                processed_photos,
                self.cache_config.mars_photos_cache_ttl
            )
            
            logger.info(
                f"Successfully retrieved {processed_photos.total_photos} Mars photos "
                f"for {validated_rover} sol {validated_sol}"
            )
            return processed_photos
            
        except NASAAPIError:
            # Re-raise NASA API errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting Mars photos: {e}")
            raise NASAAPIError(f"Failed to get Mars rover photos: {e}") from e
    
    async def get_near_earth_objects(
        self,
        start_date: str,
        end_date: str
    ) -> ProcessedNEOData:
        """
        Get Near Earth Objects data with enrichments.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            Processed NEO data with enrichments
        
        Raises:
            NASAAPIInvalidRequest: For invalid date parameters
            NASAAPIError: For API-related errors
        """
        # Validate and sanitize input
        validated_start = self._validate_neo_date(start_date, "start_date")
        validated_end = self._validate_neo_date(end_date, "end_date")
        self._validate_date_range(validated_start, validated_end)
        
        # Check cache first
        cache_key = self._generate_cache_key(
            "neo_data",
            start_date=validated_start,
            end_date=validated_end
        )
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            logger.debug(f"Returning cached NEO data for {validated_start} to {validated_end}")
            return cached_result
        
        try:
            # Get data from NASA API
            nasa_client = await self.get_nasa_client()
            neo_response = await nasa_client.get_neo_data(validated_start, validated_end)
            
            # Process and enrich data
            processed_neo = ProcessedNEOData(neo_response)
            
            # Cache the result
            self._set_in_cache(
                cache_key,
                processed_neo,
                self.cache_config.neo_cache_ttl
            )
            
            logger.info(
                f"Successfully retrieved {processed_neo.total_objects} NEO objects "
                f"for date range {validated_start} to {validated_end}"
            )
            return processed_neo
            
        except NASAAPIError:
            # Re-raise NASA API errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting NEO data: {e}")
            raise NASAAPIError(f"Failed to get Near Earth Objects data: {e}") from e
    
    # Input validation methods
    
    def _validate_apod_date(self, date_str: Optional[str]) -> Optional[str]:
        """Validate APOD date parameter."""
        if date_str is None:
            return None
        
        # Sanitize input
        date_str = date_str.strip()
        
        # Validate format
        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError as e:
            raise NASAAPIInvalidRequest(
                f"Invalid date format: {date_str}. Expected YYYY-MM-DD format."
            ) from e
        
        # Check if date is not in the future
        if parsed_date > date.today():
            raise NASAAPIInvalidRequest(
                f"Date cannot be in the future: {date_str}"
            )
        
        # Check if date is not before APOD service started (1995-06-16)
        apod_start_date = date(1995, 6, 16)
        if parsed_date < apod_start_date:
            raise NASAAPIInvalidRequest(
                f"Date cannot be before APOD service started (1995-06-16): {date_str}"
            )
        
        return date_str
    
    def _validate_rover_name(self, rover: str) -> str:
        """Validate Mars rover name."""
        if not rover or not rover.strip():
            raise NASAAPIInvalidRequest("Rover name cannot be empty")
        
        rover = rover.strip().lower()
        valid_rovers = ['curiosity', 'opportunity', 'spirit', 'perseverance']
        
        if rover not in valid_rovers:
            raise NASAAPIInvalidRequest(
                f"Invalid rover name: {rover}. Valid rovers: {', '.join(valid_rovers)}"
            )
        
        return rover
    
    def _validate_sol(self, sol: int) -> int:
        """Validate Martian sol number."""
        if not isinstance(sol, int):
            try:
                sol = int(sol)
            except (ValueError, TypeError) as e:
                raise NASAAPIInvalidRequest(f"Sol must be an integer: {sol}") from e
        
        if sol < 0:
            raise NASAAPIInvalidRequest(f"Sol cannot be negative: {sol}")
        
        # Reasonable upper limit (Mars missions haven't exceeded 10000 sols)
        if sol > 10000:
            raise NASAAPIInvalidRequest(f"Sol value too large: {sol}")
        
        return sol
    
    def _validate_camera_name(self, camera: str) -> str:
        """Validate camera name."""
        if not camera or not camera.strip():
            raise NASAAPIInvalidRequest("Camera name cannot be empty")
        
        camera = camera.strip().upper()
        
        # Valid camera names for Mars rovers
        valid_cameras = [
            'FHAZ', 'RHAZ', 'MAST', 'CHEMCAM', 'MAHLI', 'MARDI',
            'NAVCAM', 'PANCAM', 'MINITES'
        ]
        
        if camera not in valid_cameras:
            raise NASAAPIInvalidRequest(
                f"Invalid camera name: {camera}. Valid cameras: {', '.join(valid_cameras)}"
            )
        
        return camera
    
    def _validate_neo_date(self, date_str: str, param_name: str) -> str:
        """Validate NEO date parameter."""
        if not date_str or not date_str.strip():
            raise NASAAPIInvalidRequest(f"{param_name} cannot be empty")
        
        date_str = date_str.strip()
        
        # Validate format
        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError as e:
            raise NASAAPIInvalidRequest(
                f"Invalid {param_name} format: {date_str}. Expected YYYY-MM-DD format."
            ) from e
        
        # NEO data is available from 1900 onwards
        if parsed_date.year < 1900:
            raise NASAAPIInvalidRequest(
                f"{param_name} cannot be before year 1900: {date_str}"
            )
        
        # Don't allow dates too far in the future (1 year from now)
        max_future_date = date.today() + timedelta(days=365)
        if parsed_date > max_future_date:
            raise NASAAPIInvalidRequest(
                f"{param_name} cannot be more than 1 year in the future: {date_str}"
            )
        
        return date_str
    
    def _validate_date_range(self, start_date: str, end_date: str) -> None:
        """Validate date range for NEO queries."""
        start_parsed = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_parsed = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if start_parsed > end_parsed:
            raise NASAAPIInvalidRequest(
                f"Start date ({start_date}) cannot be after end date ({end_date})"
            )
        
        # NASA NEO API has a 7-day limit for date ranges
        date_diff = (end_parsed - start_parsed).days
        if date_diff > 7:
            raise NASAAPIInvalidRequest(
                f"Date range cannot exceed 7 days. Current range: {date_diff} days"
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on NASA service and API.
        
        Returns:
            Health check status and details
        """
        health_status = {
            "service": "healthy",
            "nasa_api": "unknown",
            "cache": "enabled" if self.cache else "disabled",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Check NASA API connectivity
            nasa_client = await self.get_nasa_client()
            api_healthy = await nasa_client.health_check()
            health_status["nasa_api"] = "healthy" if api_healthy else "unhealthy"
            
        except Exception as e:
            logger.warning(f"NASA API health check failed: {e}")
            health_status["nasa_api"] = "unhealthy"
            health_status["nasa_api_error"] = str(e)
        
        # Add cache statistics if enabled
        if self.cache:
            health_status["cache_stats"] = {
                "current_size": len(self.cache._cache),
                "max_size": self.cache.max_size
            }
        
        return health_status
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive performance statistics.
        
        Returns:
            Performance statistics from NASA client and service layer
        """
        stats = {
            "timestamp": datetime.now().isoformat(),
            "service_stats": {
                "cache_enabled": self.cache is not None,
                "cache_config": {
                    "apod_ttl": self.cache_config.apod_cache_ttl,
                    "mars_photos_ttl": self.cache_config.mars_photos_cache_ttl,
                    "neo_ttl": self.cache_config.neo_cache_ttl,
                    "max_size": self.cache_config.max_cache_size
                } if self.cache else None
            }
        }
        
        # Add cache statistics if enabled
        if self.cache:
            cache_stats = {
                "current_size": len(self.cache._cache),
                "max_size": self.cache.max_size,
                "hit_rate": 0.0,  # Would need to track hits/misses to calculate
                "expired_entries": 0
            }
            
            # Count expired entries
            expired_count = 0
            for entry in self.cache._cache.values():
                if entry.is_expired():
                    expired_count += 1
            cache_stats["expired_entries"] = expired_count
            
            stats["service_stats"]["cache_stats"] = cache_stats
        
        # Get NASA client performance stats if available
        if self.nasa_client:
            try:
                nasa_stats = self.nasa_client.get_performance_stats()
                stats["nasa_client_stats"] = nasa_stats
            except Exception as e:
                logger.warning("Failed to get NASA client stats", error=str(e))
                stats["nasa_client_stats"] = {"error": str(e)}
        
        return stats
    
    def clear_cache(self) -> Dict[str, Any]:
        """
        Clear the service cache.
        
        Returns:
            Cache clearing results
        """
        if not self.cache:
            return {
                "status": "no_cache",
                "message": "Caching is not enabled"
            }
        
        old_size = len(self.cache._cache)
        self.cache._cache.clear()
        self.cache._access_order.clear()
        
        logger.info("Service cache cleared", old_size=old_size)
        
        return {
            "status": "cleared",
            "entries_removed": old_size,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get detailed cache information.
        
        Returns:
            Detailed cache statistics and configuration
        """
        if not self.cache:
            return {
                "enabled": False,
                "message": "Caching is not enabled"
            }
        
        cache_info = {
            "enabled": True,
            "current_size": len(self.cache._cache),
            "max_size": self.cache.max_size,
            "configuration": {
                "apod_ttl_seconds": self.cache_config.apod_cache_ttl,
                "mars_photos_ttl_seconds": self.cache_config.mars_photos_cache_ttl,
                "neo_ttl_seconds": self.cache_config.neo_cache_ttl,
                "max_cache_size": self.cache_config.max_cache_size
            },
            "entries": []
        }
        
        # Add information about cached entries
        for key, entry in self.cache._cache.items():
            cache_info["entries"].append({
                "key": key,
                "created_at": entry.created_at.isoformat(),
                "ttl_seconds": entry.ttl,
                "is_expired": entry.is_expired(),
                "age_seconds": int((datetime.now() - entry.created_at).total_seconds())
            })
        
        return cache_info