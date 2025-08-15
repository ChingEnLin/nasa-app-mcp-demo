"""
Pydantic models for NASA API responses.

This module contains data models that represent the structure of responses
from various NASA APIs including APOD, Mars Rover Photos, and Near Earth Objects.
"""

from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class APODResponse(BaseModel):
    """Model for NASA Astronomy Picture of the Day API response."""
    
    date: str = Field(..., description="Date of the APOD image")
    title: str = Field(..., description="Title of the astronomy picture")
    explanation: str = Field(..., description="Detailed explanation of the image")
    url: HttpUrl = Field(..., description="URL of the image")
    media_type: str = Field(..., description="Type of media (image or video)")
    copyright: Optional[str] = Field(None, description="Copyright information")
    hdurl: Optional[HttpUrl] = Field(None, description="High definition image URL")
    
    @field_validator('media_type')
    @classmethod
    def validate_media_type(cls, v):
        """Validate that media_type is either 'image' or 'video'."""
        if v not in ['image', 'video']:
            raise ValueError('media_type must be either "image" or "video"')
        return v
    
    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v):
        """Validate that date is in YYYY-MM-DD format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('date must be in YYYY-MM-DD format')
        return v


class MarsPhoto(BaseModel):
    """Model for individual Mars rover photo."""
    
    id: int = Field(..., description="Unique identifier for the photo")
    img_src: HttpUrl = Field(..., description="URL of the Mars rover image")
    earth_date: str = Field(..., description="Earth date when photo was taken")
    rover_name: str = Field(..., description="Name of the Mars rover")
    camera_name: str = Field(..., description="Short name of the camera")
    camera_full_name: str = Field(..., description="Full name of the camera")
    
    @field_validator('earth_date')
    @classmethod
    def validate_earth_date_format(cls, v):
        """Validate that earth_date is in YYYY-MM-DD format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('earth_date must be in YYYY-MM-DD format')
        return v
    
    @field_validator('rover_name')
    @classmethod
    def validate_rover_name(cls, v):
        """Validate that rover_name is one of the known Mars rovers."""
        valid_rovers = ['curiosity', 'opportunity', 'spirit', 'perseverance']
        if v.lower() not in valid_rovers:
            raise ValueError(f'rover_name must be one of: {", ".join(valid_rovers)}')
        return v.lower()


class MarsRoverResponse(BaseModel):
    """Model for NASA Mars Rover Photos API response."""
    
    photos: List[MarsPhoto] = Field(..., description="List of Mars rover photos")
    rover: str = Field(..., description="Name of the rover")
    sol: int = Field(..., description="Martian sol (day) number", ge=0)
    total_photos: int = Field(..., description="Total number of photos returned", ge=0)
    
    @field_validator('rover')
    @classmethod
    def validate_rover(cls, v):
        """Validate that rover is one of the known Mars rovers."""
        valid_rovers = ['curiosity', 'opportunity', 'spirit', 'perseverance']
        if v.lower() not in valid_rovers:
            raise ValueError(f'rover must be one of: {", ".join(valid_rovers)}')
        return v.lower()


class NEOObject(BaseModel):
    """Model for individual Near Earth Object."""
    
    id: str = Field(..., description="Unique identifier for the NEO")
    name: str = Field(..., description="Name of the Near Earth Object")
    estimated_diameter_km: Dict[str, float] = Field(
        ..., 
        description="Estimated diameter range in kilometers"
    )
    is_potentially_hazardous: bool = Field(
        ..., 
        description="Whether the object is potentially hazardous"
    )
    close_approach_date: str = Field(
        ..., 
        description="Date of closest approach to Earth"
    )
    miss_distance_km: float = Field(
        ..., 
        description="Miss distance from Earth in kilometers",
        ge=0
    )
    relative_velocity_kmh: float = Field(
        ..., 
        description="Relative velocity in km/h",
        ge=0
    )
    
    @field_validator('close_approach_date')
    @classmethod
    def validate_close_approach_date(cls, v):
        """Validate that close_approach_date is in YYYY-MM-DD format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('close_approach_date must be in YYYY-MM-DD format')
        return v
    
    @field_validator('estimated_diameter_km')
    @classmethod
    def validate_diameter_range(cls, v):
        """Validate that diameter range has min and max values."""
        required_keys = {'estimated_diameter_min', 'estimated_diameter_max'}
        if not required_keys.issubset(v.keys()):
            raise ValueError(f'estimated_diameter_km must contain keys: {required_keys}')
        
        min_val = v['estimated_diameter_min']
        max_val = v['estimated_diameter_max']
        
        if min_val < 0 or max_val < 0:
            raise ValueError('diameter values must be non-negative')
        
        if min_val > max_val:
            raise ValueError('minimum diameter cannot be greater than maximum diameter')
        
        return v


class NEOResponse(BaseModel):
    """Model for NASA Near Earth Objects API response."""
    
    near_earth_objects: Dict[str, List[NEOObject]] = Field(
        ..., 
        description="Near Earth Objects grouped by date"
    )
    element_count: int = Field(
        ..., 
        description="Total number of NEO elements",
        ge=0
    )
    date_range: Dict[str, str] = Field(
        ..., 
        description="Date range for the query"
    )
    
    @field_validator('date_range')
    @classmethod
    def validate_date_range(cls, v):
        """Validate that date_range has start_date and end_date."""
        required_keys = {'start_date', 'end_date'}
        if not required_keys.issubset(v.keys()):
            raise ValueError(f'date_range must contain keys: {required_keys}')
        
        # Validate date formats
        try:
            start_date = datetime.strptime(v['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(v['end_date'], '%Y-%m-%d')
        except ValueError:
            raise ValueError('dates in date_range must be in YYYY-MM-DD format')
        
        if start_date > end_date:
            raise ValueError('start_date cannot be after end_date')
        
        return v