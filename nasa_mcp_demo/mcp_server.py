"""
MCP (Model Context Protocol) server integration for NASA MCP Demo.

This module provides MCP server functionality that integrates with the existing
FastAPI application, allowing AI models to access NASA data through MCP tools.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import structlog
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

from .models.config import AppConfig
from .services.nasa_service import NASAService
from .models.errors import NASAAPIError, NASAAPIInvalidRequest

logger = structlog.get_logger(__name__)


class NASAMCPServer:
    """MCP server wrapper for NASA data access."""
    
    def __init__(self, app: FastAPI, config: AppConfig, nasa_service: NASAService):
        """Initialize MCP server with NASA service integration."""
        self.app = app
        self.config = config
        self.nasa_service = nasa_service
        self.mcp_server: Optional[FastApiMCP] = None
        self._tools_count = 0
        
        if config.enable_mcp:
            self._setup_mcp_server()
    
    def _setup_mcp_server(self) -> None:
        """Set up MCP server with NASA tools."""
        try:
            # Add MCP endpoints to the FastAPI app first
            self._add_mcp_endpoints()
            
            # Create MCP server instance that will expose FastAPI endpoints as MCP tools
            self.mcp_server = FastApiMCP(
                fastapi=self.app,
                name=self.config.mcp_server_name,
                description="NASA data access through MCP protocol"
            )
            
            self._tools_count = 3  # We're adding 3 MCP endpoints
            
            logger.info(
                "MCP server initialized successfully",
                server_name=self.config.mcp_server_name,
                tools_count=self._tools_count
            )
            
        except Exception as e:
            logger.error("Failed to initialize MCP server", error=str(e))
            raise
    
    def _add_mcp_endpoints(self) -> None:
        """Add MCP-specific endpoints to the FastAPI app."""
        from fastapi import Query
        from pydantic import BaseModel
        
        # APOD MCP endpoint
        @self.app.post("/mcp/tools/get_astronomy_picture", tags=["MCP Tools"])
        async def get_astronomy_picture_mcp(
            date: Optional[str] = Query(
                None,
                description="Date in YYYY-MM-DD format. If not provided, returns today's APOD"
            )
        ) -> Dict[str, Any]:
            """
            Get NASA's Astronomy Picture of the Day (APOD) with detailed information and metadata.
            
            The APOD service provides a different astronomy or space science image 
            each day along with a brief explanation written by a professional astronomer.
            """
            try:
                processed_apod = await self.nasa_service.get_daily_astronomy_picture(date)
                result = processed_apod.to_dict()
                
                # Add metadata for AI consumption
                result["_metadata"] = {
                    "source": "NASA APOD API",
                    "retrieved_at": datetime.now().isoformat(),
                    "data_type": "astronomy_picture",
                    "content_summary": f"Astronomy picture titled '{result['title']}' from {result['date']}"
                }
                
                return result
                
            except NASAAPIInvalidRequest as e:
                logger.warning("Invalid APOD request", error=str(e), date=date)
                raise Exception(f"Invalid request: {str(e)}")
            except NASAAPIError as e:
                logger.error("NASA API error for APOD", error=str(e), date=date)
                raise Exception(f"NASA API error: {str(e)}")
            except Exception as e:
                logger.error("Unexpected error getting APOD", error=str(e), date=date)
                raise Exception(f"Failed to get astronomy picture: {str(e)}")
        
        # Mars rover photos MCP endpoint
        class MarsPhotosRequest(BaseModel):
            rover: str
            sol: int
            camera: Optional[str] = None
        
        @self.app.post("/mcp/tools/search_mars_rover_photos", tags=["MCP Tools"])
        async def search_mars_rover_photos_mcp(
            request: MarsPhotosRequest
        ) -> Dict[str, Any]:
            """
            Search for photos taken by Mars exploration rovers with detailed metadata and analysis.
            
            Mars rovers have been exploring the Red Planet for decades, capturing thousands 
            of images that help scientists understand Mars' geology, climate, and potential 
            for past or present life.
            """
            try:
                processed_photos = await self.nasa_service.search_mars_photos(
                    request.rover, request.sol, request.camera
                )
                result = processed_photos.to_dict()
                
                # Add metadata for AI consumption
                result["_metadata"] = {
                    "source": "NASA Mars Rover Photos API",
                    "retrieved_at": datetime.now().isoformat(),
                    "data_type": "mars_rover_photos",
                    "content_summary": f"{result['total_photos']} photos from {request.rover} rover on sol {request.sol}",
                    "rover_info": {
                        "name": request.rover,
                        "sol": request.sol,
                        "camera_filter": request.camera,
                        "mission_context": self._get_rover_context(request.rover)
                    }
                }
                
                return result
                
            except NASAAPIInvalidRequest as e:
                logger.warning("Invalid Mars photos request", error=str(e), rover=request.rover, sol=request.sol, camera=request.camera)
                raise Exception(f"Invalid request: {str(e)}")
            except NASAAPIError as e:
                logger.error("NASA API error for Mars photos", error=str(e), rover=request.rover, sol=request.sol)
                raise Exception(f"NASA API error: {str(e)}")
            except Exception as e:
                logger.error("Unexpected error getting Mars photos", error=str(e), rover=request.rover, sol=request.sol)
                raise Exception(f"Failed to get Mars rover photos: {str(e)}")
        
        # NEO MCP endpoint
        class NEORequest(BaseModel):
            start_date: str
            end_date: str
        
        @self.app.post("/mcp/tools/find_near_earth_objects", tags=["MCP Tools"])
        async def find_near_earth_objects_mcp(
            request: NEORequest
        ) -> Dict[str, Any]:
            """
            Find Near Earth Objects (asteroids and comets) with comprehensive analysis and risk assessment.
            
            NASA tracks these objects to understand potential impact risks and for scientific study.
            This tool provides comprehensive analysis including size categorization, speed analysis,
            and hazard assessment.
            """
            try:
                processed_neo = await self.nasa_service.get_near_earth_objects(
                    request.start_date, request.end_date
                )
                result = processed_neo.to_dict()
                
                # Add metadata for AI consumption
                result["_metadata"] = {
                    "source": "NASA Near Earth Object Web Service (NeoWs)",
                    "retrieved_at": datetime.now().isoformat(),
                    "data_type": "near_earth_objects",
                    "content_summary": f"{result['total_objects']} NEO objects from {request.start_date} to {request.end_date}",
                    "analysis_summary": {
                        "total_objects": result['total_objects'],
                        "hazardous_objects": result['hazardous_count'],
                        "date_range_days": (datetime.strptime(request.end_date, '%Y-%m-%d') - 
                                          datetime.strptime(request.start_date, '%Y-%m-%d')).days + 1,
                        "size_distribution": result['size_categories'],
                        "has_close_approaches": result['closest_approach'] is not None,
                        "has_fast_objects": result['fastest_object'] is not None
                    }
                }
                
                return result
                
            except NASAAPIInvalidRequest as e:
                logger.warning("Invalid NEO request", error=str(e), start_date=request.start_date, end_date=request.end_date)
                raise Exception(f"Invalid request: {str(e)}")
            except NASAAPIError as e:
                logger.error("NASA API error for NEO", error=str(e), start_date=request.start_date, end_date=request.end_date)
                raise Exception(f"NASA API error: {str(e)}")
            except Exception as e:
                logger.error("Unexpected error getting NEO data", error=str(e), start_date=request.start_date, end_date=request.end_date)
                raise Exception(f"Failed to get Near Earth Objects data: {str(e)}")
        
        logger.info("NASA MCP endpoints added successfully", endpoints_count=3)
    
    def _get_rover_context(self, rover: str) -> str:
        """Get contextual information about a Mars rover."""
        rover_contexts = {
            "curiosity": "Nuclear-powered rover with advanced scientific instruments, active since 2012",
            "perseverance": "Advanced rover searching for signs of ancient microbial life, active since 2021",
            "opportunity": "Long-duration rover that operated for nearly 15 years (2004-2018)",
            "spirit": "First of the Mars Exploration Rovers, operated 2004-2010"
        }
        return rover_contexts.get(rover.lower(), f"Mars exploration rover: {rover}")
    
    def is_enabled(self) -> bool:
        """Check if MCP server is enabled and initialized."""
        return self.config.enable_mcp and self.mcp_server is not None
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get MCP server information."""
        if not self.is_enabled():
            return {
                "enabled": False,
                "reason": "MCP server not enabled in configuration"
            }
        
        return {
            "enabled": True,
            "server_name": self.config.mcp_server_name,
            "version": "1.0.0",
            "description": "NASA data access through MCP protocol",
            "tools_available": self._tools_count,
            "protocol_version": "1.0",
            "tools": [
                {
                    "name": "get_astronomy_picture",
                    "description": "Get NASA's Astronomy Picture of the Day with metadata"
                },
                {
                    "name": "search_mars_rover_photos", 
                    "description": "Search Mars rover photos with analysis"
                },
                {
                    "name": "find_near_earth_objects",
                    "description": "Find Near Earth Objects with risk assessment"
                }
            ]
        }


def create_mcp_server(app: FastAPI, config: AppConfig, nasa_service: NASAService) -> NASAMCPServer:
    """Factory function to create and configure MCP server."""
    return NASAMCPServer(app, config, nasa_service)