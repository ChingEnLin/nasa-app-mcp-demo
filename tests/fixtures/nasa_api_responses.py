"""
Mock NASA API responses for consistent testing.

This module provides realistic mock responses for all NASA API endpoints
used in the application, ensuring consistent and predictable test data.
"""

from datetime import date, datetime, timedelta
from typing import Dict, Any, List


class MockNASAResponses:
    """Collection of mock NASA API responses for testing."""
    
    @staticmethod
    def get_apod_response(
        date_str: str = None,
        media_type: str = "image",
        include_copyright: bool = True,
        include_hdurl: bool = True
    ) -> Dict[str, Any]:
        """Generate mock APOD response."""
        if date_str is None:
            date_str = date.today().strftime('%Y-%m-%d')
        
        response = {
            "date": date_str,
            "title": f"Amazing Space Photo for {date_str}",
            "explanation": (
                "This stunning image captures the beauty of our universe. "
                "The intricate details visible in this photograph showcase "
                "the incredible complexity and wonder of space. Scientists "
                "continue to study these phenomena to better understand "
                "the cosmos and our place within it."
            ),
            "url": f"https://apod.nasa.gov/apod/image/{date_str.replace('-', '')}/test_image.jpg",
            "media_type": media_type
        }
        
        if include_copyright:
            response["copyright"] = "NASA/ESA/Hubble Space Telescope"
        
        if include_hdurl and media_type == "image":
            response["hdurl"] = f"https://apod.nasa.gov/apod/image/{date_str.replace('-', '')}/test_image_hd.jpg"
        
        if media_type == "video":
            response["url"] = f"https://www.youtube.com/embed/test_video_{date_str.replace('-', '')}"
        
        return response
    
    @staticmethod
    def get_mars_rover_response(
        rover: str = "curiosity",
        sol: int = 1000,
        camera: str = None,
        photo_count: int = 5
    ) -> Dict[str, Any]:
        """Generate mock Mars rover photos response."""
        photos = []
        
        cameras = ["FHAZ", "RHAZ", "MAST", "CHEMCAM", "MAHLI", "MARDI", "NAVCAM"]
        if camera:
            cameras = [camera.upper()]
        
        camera_full_names = {
            "FHAZ": "Front Hazard Avoidance Camera",
            "RHAZ": "Rear Hazard Avoidance Camera", 
            "MAST": "Mast Camera",
            "CHEMCAM": "Chemistry and Camera Complex",
            "MAHLI": "Mars Hand Lens Imager",
            "MARDI": "Mars Descent Imager",
            "NAVCAM": "Navigation Camera"
        }
        
        earth_date = (date.today() - timedelta(days=sol)).strftime('%Y-%m-%d')
        
        for i in range(photo_count):
            cam = cameras[i % len(cameras)]
            photos.append({
                "id": 100000 + i,
                "img_src": f"https://mars.nasa.gov/msl-raw-images/proj/msl/redops/ods/surface/sol/{sol:05d}/opgs/edr/fcam/{rover}_{sol:05d}_{cam}_{i:03d}.jpg",
                "earth_date": earth_date,
                "rover_name": rover,
                "camera_name": cam,
                "camera_full_name": camera_full_names.get(cam, f"{cam} Camera")
            })
        
        return {
            "photos": photos,
            "rover": rover,
            "sol": sol,
            "total_photos": len(photos)
        }
    
    @staticmethod
    def get_neo_response(
        start_date: str,
        end_date: str,
        object_count: int = 3
    ) -> Dict[str, Any]:
        """Generate mock NEO (Near Earth Objects) response."""
        near_earth_objects = {}
        
        # Parse dates
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        current_date = start
        total_objects = 0
        
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            objects_for_date = []
            
            # Generate 0-3 objects per date
            objects_today = min(object_count, 3) if current_date == start else (object_count // 3)
            
            for i in range(objects_today):
                obj_id = f"{current_date.strftime('%Y%m%d')}{i:03d}"
                
                # Vary object properties for realistic data
                is_hazardous = i == 0  # Make first object potentially hazardous
                diameter_min = 0.1 + (i * 0.5)
                diameter_max = diameter_min + 0.3
                miss_distance = 1000000 + (i * 500000)  # km
                velocity = 20000 + (i * 15000)  # km/h
                
                objects_for_date.append({
                    "id": obj_id,
                    "name": f"({obj_id}) Test Asteroid {i+1}",
                    "estimated_diameter_km": {
                        "estimated_diameter_min": diameter_min,
                        "estimated_diameter_max": diameter_max
                    },
                    "is_potentially_hazardous": is_hazardous,
                    "close_approach_date": date_str,
                    "miss_distance_km": miss_distance,
                    "relative_velocity_kmh": velocity
                })
                total_objects += 1
            
            if objects_for_date:
                near_earth_objects[date_str] = objects_for_date
            
            current_date += timedelta(days=1)
        
        return {
            "element_count": total_objects,
            "near_earth_objects": near_earth_objects,
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
    
    @staticmethod
    def get_error_response(
        status_code: int,
        error_message: str = None,
        error_code: str = None
    ) -> Dict[str, Any]:
        """Generate mock error response."""
        if error_message is None:
            error_messages = {
                400: "Bad Request - Invalid parameters",
                403: "Forbidden - API key invalid or missing",
                404: "Not Found - Resource not found",
                429: "Too Many Requests - Rate limit exceeded",
                500: "Internal Server Error - NASA API temporarily unavailable",
                502: "Bad Gateway - NASA API is down",
                503: "Service Unavailable - NASA API maintenance"
            }
            error_message = error_messages.get(status_code, "Unknown error")
        
        response = {
            "error": {
                "code": error_code or f"HTTP_{status_code}",
                "message": error_message
            }
        }
        
        # Add specific fields for certain error types
        if status_code == 429:
            response["error"]["retry_after"] = 60
        elif status_code == 403:
            response["error"]["details"] = "Check your API key and ensure it's valid"
        
        return response


# Pre-defined test data sets
SAMPLE_APOD_RESPONSES = {
    "image_with_copyright": MockNASAResponses.get_apod_response(
        date_str="2023-12-01",
        media_type="image",
        include_copyright=True,
        include_hdurl=True
    ),
    "image_no_copyright": MockNASAResponses.get_apod_response(
        date_str="2023-12-02", 
        media_type="image",
        include_copyright=False,
        include_hdurl=True
    ),
    "video": MockNASAResponses.get_apod_response(
        date_str="2023-12-03",
        media_type="video",
        include_copyright=True,
        include_hdurl=False
    ),
    "recent": MockNASAResponses.get_apod_response(
        date_str=date.today().strftime('%Y-%m-%d'),
        media_type="image"
    )
}

SAMPLE_MARS_RESPONSES = {
    "curiosity_multiple_cameras": MockNASAResponses.get_mars_rover_response(
        rover="curiosity",
        sol=1000,
        photo_count=10
    ),
    "perseverance_mast_only": MockNASAResponses.get_mars_rover_response(
        rover="perseverance",
        sol=500,
        camera="MAST",
        photo_count=5
    ),
    "opportunity_no_photos": MockNASAResponses.get_mars_rover_response(
        rover="opportunity",
        sol=2000,
        photo_count=0
    )
}

SAMPLE_NEO_RESPONSES = {
    "single_day_multiple_objects": MockNASAResponses.get_neo_response(
        start_date="2023-12-01",
        end_date="2023-12-01",
        object_count=3
    ),
    "week_range_varied_objects": MockNASAResponses.get_neo_response(
        start_date="2023-12-01", 
        end_date="2023-12-07",
        object_count=15
    ),
    "no_objects": {
        "element_count": 0,
        "near_earth_objects": {}
    }
}

ERROR_RESPONSES = {
    "rate_limited": MockNASAResponses.get_error_response(429),
    "invalid_api_key": MockNASAResponses.get_error_response(403),
    "bad_request": MockNASAResponses.get_error_response(400),
    "server_error": MockNASAResponses.get_error_response(500),
    "service_unavailable": MockNASAResponses.get_error_response(503)
}