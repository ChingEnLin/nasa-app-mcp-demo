"""
FastAPI application for NASA MCP Demo.

This module contains the main FastAPI application with REST endpoints
for NASA data including APOD, Mars rover photos, and Near Earth Objects.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, Query, Path, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
from pydantic import BaseModel, Field
import structlog

from .models.config import AppConfig
from .models.errors import NASAAPIError, NASAAPIInvalidRequest, NASAAPIUnavailable, NASAAPIRateLimited
from .services.nasa_service import NASAService
from .logging_config import setup_logging


# Configure structured logging
logger = structlog.get_logger(__name__)

# Global app configuration
app_config: Optional[AppConfig] = None
nasa_service: Optional[NASAService] = None


# Response models for API documentation
class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: str = Field(..., description="Error timestamp in ISO format")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Overall health status")
    service: str = Field(..., description="Service health status")
    nasa_api: str = Field(..., description="NASA API connectivity status")
    cache: str = Field(..., description="Cache status")
    timestamp: str = Field(..., description="Health check timestamp")
    cache_stats: Optional[Dict[str, int]] = Field(None, description="Cache statistics")
    nasa_api_error: Optional[str] = Field(None, description="NASA API error details")


class APODResponseModel(BaseModel):
    """APOD API response model."""
    date: str = Field(..., description="Date of the astronomy picture")
    title: str = Field(..., description="Title of the picture")
    explanation: str = Field(..., description="Detailed explanation")
    url: str = Field(..., description="Image/video URL")
    media_type: str = Field(..., description="Media type (image or video)")
    copyright: Optional[str] = Field(None, description="Copyright information")
    hdurl: Optional[str] = Field(None, description="High definition URL")
    is_image: bool = Field(..., description="Whether the media is an image")
    is_video: bool = Field(..., description="Whether the media is a video")
    has_hd_version: bool = Field(..., description="Whether HD version is available")
    word_count: int = Field(..., description="Word count of explanation")
    is_recent: bool = Field(..., description="Whether the picture is from last 30 days")


class MarsPhotosResponseModel(BaseModel):
    """Mars rover photos API response model."""
    rover: str = Field(..., description="Rover name")
    sol: int = Field(..., description="Martian sol number")
    total_photos: int = Field(..., description="Total number of photos")
    photos: List[Dict[str, Any]] = Field(..., description="List of photos with metadata")
    cameras_used: List[str] = Field(..., description="List of cameras used")
    earth_dates: List[str] = Field(..., description="Earth dates of photos")
    has_photos: bool = Field(..., description="Whether any photos were found")
    camera_summary: Dict[str, int] = Field(..., description="Photo count by camera")


class NEOResponseModel(BaseModel):
    """Near Earth Objects API response model."""
    element_count: int = Field(..., description="Total number of NEO elements")
    date_range: Dict[str, str] = Field(..., description="Query date range")
    near_earth_objects: Dict[str, List[Dict[str, Any]]] = Field(..., description="NEO objects by date")
    total_objects: int = Field(..., description="Total number of objects found")
    hazardous_count: int = Field(..., description="Number of potentially hazardous objects")
    size_categories: Dict[str, int] = Field(..., description="Objects grouped by size category")
    closest_approach: Optional[Dict[str, Any]] = Field(None, description="Object with closest approach")
    fastest_object: Optional[Dict[str, Any]] = Field(None, description="Fastest moving object")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    global app_config, nasa_service
    
    logger.info("Starting NASA MCP Demo application")
    
    # Load configuration
    app_config = AppConfig()
    
    # Setup logging
    setup_logging(app_config.logging)
    
    # Initialize NASA service
    nasa_service = NASAService(app_config)
    
    logger.info("Application startup complete", 
                app_name=app_config.app_name,
                version=app_config.app_version,
                debug=app_config.debug)
    
    yield
    
    # Shutdown
    logger.info("Shutting down NASA MCP Demo application")


# Create FastAPI application
app = FastAPI(
    title="NASA Data API",
    description="""
    Educational demo for NASA API integration with FastAPI.
    
    This API provides access to NASA's public data including:
    - **Astronomy Picture of the Day (APOD)**: Daily space images with explanations
    - **Mars Rover Photos**: Images from Mars exploration rovers
    - **Near Earth Objects (NEO)**: Asteroid and comet tracking data
    
    The API demonstrates best practices for:
    - Async HTTP client integration
    - Data validation and transformation
    - Error handling and logging
    - API documentation
    - Caching strategies
    
    This serves as the baseline implementation before adding MCP (Model Context Protocol) capabilities.
    """,
    version="1.0.0",
    contact={
        "name": "NASA MCP Demo",
        "url": "https://github.com/example/nasa-mcp-demo",
        "email": "demo@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configure middleware (must be done before app starts)
# Load config for middleware setup
temp_config = AppConfig()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=temp_config.cors_origins,
    allow_credentials=temp_config.cors_allow_credentials,
    allow_methods=temp_config.cors_allow_methods,
    allow_headers=temp_config.cors_allow_headers,
)

# Add trusted host middleware in production
if not temp_config.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure based on deployment
    )


# Dependency to get NASA service
async def get_nasa_service() -> NASAService:
    """Dependency to get NASA service instance."""
    if nasa_service is None:
        raise HTTPException(
            status_code=500,
            detail="NASA service not initialized"
        )
    return nasa_service


# Dependency to get app config
async def get_app_config() -> AppConfig:
    """Dependency to get app configuration."""
    if app_config is None:
        raise HTTPException(
            status_code=500,
            detail="Application configuration not loaded"
        )
    return app_config


# Custom exception handlers
@app.exception_handler(NASAAPIInvalidRequest)
async def nasa_invalid_request_handler(request: Request, exc: NASAAPIInvalidRequest):
    """Handle NASA API invalid request errors."""
    logger.warning("Invalid request", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error="invalid_request",
            message=str(exc),
            timestamp=datetime.now().isoformat(),
            request_id=getattr(request.state, 'request_id', None)
        ).dict()
    )


@app.exception_handler(NASAAPIRateLimited)
async def nasa_rate_limited_handler(request: Request, exc: NASAAPIRateLimited):
    """Handle NASA API rate limit errors."""
    logger.warning("Rate limited", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=429,
        content=ErrorResponse(
            error="rate_limited",
            message=str(exc),
            details={"retry_after": "3600"},
            timestamp=datetime.now().isoformat(),
            request_id=getattr(request.state, 'request_id', None)
        ).dict(),
        headers={"Retry-After": "3600"}
    )


@app.exception_handler(NASAAPIUnavailable)
async def nasa_unavailable_handler(request: Request, exc: NASAAPIUnavailable):
    """Handle NASA API unavailable errors."""
    logger.error("NASA API unavailable", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error="service_unavailable",
            message=str(exc),
            details={"service": "NASA API"},
            timestamp=datetime.now().isoformat(),
            request_id=getattr(request.state, 'request_id', None)
        ).dict(),
        headers={"Retry-After": "300"}
    )


@app.exception_handler(NASAAPIError)
async def nasa_api_error_handler(request: Request, exc: NASAAPIError):
    """Handle general NASA API errors."""
    logger.error("NASA API error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=502,
        content=ErrorResponse(
            error="api_error",
            message=str(exc),
            details={"service": "NASA API"},
            timestamp=datetime.now().isoformat(),
            request_id=getattr(request.state, 'request_id', None)
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error("Unexpected error", error=str(exc), path=request.url.path, exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_error",
            message="An unexpected error occurred",
            timestamp=datetime.now().isoformat(),
            request_id=getattr(request.state, 'request_id', None)
        ).dict()
    )


# Middleware configuration
async def add_request_id_middleware(request: Request, call_next):
    """Add request ID to all requests for tracking."""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Add request ID to structured logging context
    with structlog.contextvars.bound_contextvars(request_id=request_id):
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


async def logging_middleware(request: Request, call_next):
    """Log all requests and responses."""
    start_time = datetime.now()
    
    # Log request
    logger.info("Request started",
                method=request.method,
                path=request.url.path,
                query_params=str(request.query_params),
                client_ip=request.client.host if request.client else None)
    
    response = await call_next(request)
    
    # Calculate duration
    duration = (datetime.now() - start_time).total_seconds()
    
    # Log response
    logger.info("Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_seconds=duration)
    
    return response


# Add HTTP middleware
app.middleware("http")(add_request_id_middleware)
app.middleware("http")(logging_middleware)





# API Endpoints

@app.get("/", 
         summary="API Root",
         description="Get basic API information and available endpoints")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "NASA Data API",
        "version": "1.0.0",
        "description": "Educational demo for NASA API integration with FastAPI",
        "endpoints": {
            "apod": "/apod - Astronomy Picture of the Day",
            "mars_photos": "/mars-photos/{rover} - Mars rover photos",
            "neo": "/neo - Near Earth Objects",
            "health": "/health - Health check",
            "docs": "/docs - API documentation"
        },
        "nasa_apis": [
            "Astronomy Picture of the Day (APOD)",
            "Mars Rover Photos",
            "Near Earth Objects (NEO)"
        ]
    }


@app.get("/health",
         response_model=HealthResponse,
         summary="Health Check",
         description="Check the health status of the API and NASA service connectivity")
async def health_check(service: NASAService = Depends(get_nasa_service)):
    """
    Perform comprehensive health check.
    
    Returns the health status of:
    - This API service
    - NASA API connectivity
    - Cache system status
    - Additional diagnostic information
    """
    try:
        health_data = await service.health_check()
        
        # Determine overall status
        overall_status = "healthy"
        if health_data.get("nasa_api") == "unhealthy":
            overall_status = "degraded"
        
        return HealthResponse(
            status=overall_status,
            service=health_data["service"],
            nasa_api=health_data["nasa_api"],
            cache=health_data["cache"],
            timestamp=health_data["timestamp"],
            cache_stats=health_data.get("cache_stats"),
            nasa_api_error=health_data.get("nasa_api_error")
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthResponse(
            status="unhealthy",
            service="unhealthy",
            nasa_api="unknown",
            cache="unknown",
            timestamp=datetime.now().isoformat(),
            nasa_api_error=str(e)
        )


@app.get("/apod",
         response_model=APODResponseModel,
         summary="Astronomy Picture of the Day",
         description="Get NASA's Astronomy Picture of the Day with enriched metadata")
async def get_apod(
    date: Optional[str] = Query(
        None,
        description="Date in YYYY-MM-DD format. If not provided, returns today's APOD",
        examples=["2024-01-15"],
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    service: NASAService = Depends(get_nasa_service)
):
    """
    Get Astronomy Picture of the Day (APOD) from NASA.
    
    The APOD service has been running since June 16, 1995, providing a different
    astronomy or space science image each day along with a brief explanation.
    
    **Features:**
    - Daily space images and videos
    - Detailed explanations by professional astronomers
    - High-definition versions when available
    - Enriched metadata including word count and recency
    
    **Parameters:**
    - **date**: Optional date in YYYY-MM-DD format
      - If not provided, returns today's APOD
      - Cannot be in the future
      - Cannot be before June 16, 1995 (service start date)
    
    **Returns:**
    - Complete APOD data with enrichments
    - Media type detection (image/video)
    - HD version availability
    - Content analysis (word count, recency)
    """
    try:
        processed_apod = await service.get_daily_astronomy_picture(date)
        return APODResponseModel(**processed_apod.to_dict())
    except (NASAAPIError, NASAAPIInvalidRequest):
        # These will be handled by custom exception handlers
        raise


@app.get("/mars-photos/{rover}",
         response_model=MarsPhotosResponseModel,
         summary="Mars Rover Photos",
         description="Get photos from Mars exploration rovers with enriched metadata")
async def get_mars_photos(
    rover: str = Path(
        ...,
        description="Mars rover name",
        examples=["curiosity"]
    ),
    sol: int = Query(
        ...,
        description="Martian sol (day) number",
        examples=[1000],
        ge=0
    ),
    camera: Optional[str] = Query(
        None,
        description="Camera name filter (optional)",
        examples=["MAST"]
    ),
    service: NASAService = Depends(get_nasa_service)
):
    """
    Get photos from Mars exploration rovers.
    
    Mars rovers have been exploring the Red Planet for decades, capturing
    thousands of images that help scientists understand Mars' geology,
    climate, and potential for past or present life.
    
    **Supported Rovers:**
    - **curiosity**: Active since 2012, advanced scientific instruments
    - **perseverance**: Active since 2021, searching for signs of ancient life
    - **opportunity**: Active 2004-2018, geological surveys
    - **spirit**: Active 2004-2010, geological surveys
    
    **Camera Types:**
    - **FHAZ/RHAZ**: Front/Rear Hazard Avoidance Cameras
    - **MAST**: Mast Camera (color imaging)
    - **NAVCAM**: Navigation Camera
    - **CHEMCAM**: Chemistry and Camera Complex
    - **MAHLI**: Mars Hand Lens Imager
    - **MARDI**: Mars Descent Imager
    - **PANCAM**: Panoramic Camera (Spirit/Opportunity)
    
    **Parameters:**
    - **rover**: Name of the Mars rover
    - **sol**: Martian sol (day) number since landing
    - **camera**: Optional camera filter
    
    **Returns:**
    - List of photos with metadata
    - Camera usage summary
    - Earth dates and rover information
    - Enhanced metadata (camera types, color detection)
    """
    try:
        processed_photos = await service.search_mars_photos(rover, sol, camera)
        return MarsPhotosResponseModel(**processed_photos.to_dict())
    except (NASAAPIError, NASAAPIInvalidRequest):
        # These will be handled by custom exception handlers
        raise


@app.get("/neo",
         response_model=NEOResponseModel,
         summary="Near Earth Objects",
         description="Get Near Earth Objects (asteroids and comets) data with analysis")
async def get_neo_data(
    start_date: str = Query(
        ...,
        description="Start date in YYYY-MM-DD format",
        examples=["2024-01-01"],
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    end_date: str = Query(
        ...,
        description="End date in YYYY-MM-DD format",
        examples=["2024-01-07"],
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    service: NASAService = Depends(get_nasa_service)
):
    """
    Get Near Earth Objects (NEO) data from NASA.
    
    Near Earth Objects are asteroids and comets whose orbits bring them
    close to Earth's orbit. NASA tracks these objects to understand
    potential impact risks and for scientific study.
    
    **Object Categories:**
    - **Asteroids**: Rocky objects from the asteroid belt
    - **Comets**: Icy objects from the outer solar system
    - **Potentially Hazardous**: Objects that could pose impact risk
    
    **Data Analysis:**
    - Size categorization (Very Small to Very Large)
    - Speed analysis (Slow to Very Fast)
    - Distance classification (Closer than Moon to Far)
    - Hazard assessment
    
    **Parameters:**
    - **start_date**: Query start date (YYYY-MM-DD)
    - **end_date**: Query end date (YYYY-MM-DD)
    - Date range cannot exceed 7 days (NASA API limitation)
    
    **Returns:**
    - NEO objects grouped by date
    - Statistical analysis and categorization
    - Closest approach and fastest object identification
    - Hazard assessment summary
    """
    try:
        processed_neo = await service.get_near_earth_objects(start_date, end_date)
        return NEOResponseModel(**processed_neo.to_dict())
    except (NASAAPIError, NASAAPIInvalidRequest):
        # These will be handled by custom exception handlers
        raise


# Additional utility endpoints

@app.get("/rovers",
         summary="Available Mars Rovers",
         description="Get list of available Mars rovers and their information")
async def get_available_rovers():
    """
    Get information about available Mars rovers.
    
    Returns details about each rover including mission dates,
    landing information, and available cameras.
    """
    return {
        "rovers": {
            "curiosity": {
                "name": "Curiosity",
                "landing_date": "2012-08-05",
                "status": "active",
                "mission": "Mars Science Laboratory",
                "cameras": ["FHAZ", "RHAZ", "MAST", "CHEMCAM", "MAHLI", "MARDI", "NAVCAM"],
                "description": "Nuclear-powered rover with advanced scientific instruments"
            },
            "perseverance": {
                "name": "Perseverance",
                "landing_date": "2021-02-18",
                "status": "active",
                "mission": "Mars 2020",
                "cameras": ["FHAZ", "RHAZ", "MAST", "NAVCAM"],
                "description": "Advanced rover searching for signs of ancient microbial life"
            },
            "opportunity": {
                "name": "Opportunity",
                "landing_date": "2004-01-25",
                "mission_end": "2018-06-10",
                "status": "inactive",
                "mission": "Mars Exploration Rover B",
                "cameras": ["FHAZ", "RHAZ", "NAVCAM", "PANCAM"],
                "description": "Long-duration rover that operated for nearly 15 years"
            },
            "spirit": {
                "name": "Spirit",
                "landing_date": "2004-01-04",
                "mission_end": "2010-03-22",
                "status": "inactive",
                "mission": "Mars Exploration Rover A",
                "cameras": ["FHAZ", "RHAZ", "NAVCAM", "PANCAM"],
                "description": "First of the Mars Exploration Rovers"
            }
        },
        "camera_descriptions": {
            "FHAZ": "Front Hazard Avoidance Camera",
            "RHAZ": "Rear Hazard Avoidance Camera",
            "MAST": "Mast Camera",
            "CHEMCAM": "Chemistry and Camera Complex",
            "MAHLI": "Mars Hand Lens Imager",
            "MARDI": "Mars Descent Imager",
            "NAVCAM": "Navigation Camera",
            "PANCAM": "Panoramic Camera"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # Load config for development server
    config = AppConfig()
    
    uvicorn.run(
        "nasa_mcp_demo.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level=config.logging.level.lower()
    )