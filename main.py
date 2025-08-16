import os
import httpx
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Simple NASA MCP Server",
    description="A simple FastAPI server providing NASA data through REST endpoints",
    version="1.0.0"
)

# NASA API configuration
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
NASA_BASE_URL = "https://api.nasa.gov"

# HTTP client for NASA API calls
client = httpx.AsyncClient(timeout=30.0)

# Response models
class APODResponse(BaseModel):
    title: str
    explanation: str
    url: str
    date: str
    media_type: str
    hdurl: Optional[str] = None
    copyright: Optional[str] = None

class MarsPhotoResponse(BaseModel):
    id: int
    sol: int
    camera: Dict[str, Any]
    img_src: str
    earth_date: str
    rover: Dict[str, Any]

class MarsPhotosResponse(BaseModel):
    photos: List[MarsPhotoResponse]

class NEOResponse(BaseModel):
    id: str
    name: str
    estimated_diameter: Dict[str, Any]
    is_potentially_hazardous_asteroid: bool
    close_approach_data: List[Dict[str, Any]]

class NEOFeedResponse(BaseModel):
    element_count: int
    near_earth_objects: Dict[str, List[NEOResponse]]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "simple-nasa-mcp"}

@app.get("/apod", response_model=APODResponse)
async def get_astronomy_picture_of_day(date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format")):
    """Get NASA's Astronomy Picture of the Day"""
    try:
        params = {"api_key": NASA_API_KEY}
        if date:
            params["date"] = date
            
        response = await client.get(f"{NASA_BASE_URL}/planetary/apod", params=params)
        
        if response.status_code == 200:
            data = response.json()
            return APODResponse(**data)
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"NASA API error: {response.text}"
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Failed to connect to NASA API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/mars-photos", response_model=MarsPhotosResponse)
async def get_mars_rover_photos(
    rover: str = Query(..., description="Rover name (curiosity, perseverance, opportunity, spirit)"),
    sol: int = Query(..., description="Martian sol (day) number"),
    camera: Optional[str] = Query(None, description="Camera name (FHAZ, RHAZ, MAST, NAVCAM, etc.)")
):
    """Get Mars rover photos"""
    try:
        params = {
            "api_key": NASA_API_KEY,
            "sol": sol
        }
        if camera:
            params["camera"] = camera
            
        response = await client.get(f"{NASA_BASE_URL}/mars-photos/api/v1/rovers/{rover}/photos", params=params)
        
        if response.status_code == 200:
            data = response.json()
            return MarsPhotosResponse(**data)
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"NASA API error: {response.text}"
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Failed to connect to NASA API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/neo", response_model=NEOFeedResponse)
async def get_near_earth_objects(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format")
):
    """Get Near Earth Objects (asteroids and comets)"""
    try:
        params = {
            "api_key": NASA_API_KEY,
            "start_date": start_date,
            "end_date": end_date
        }
        
        response = await client.get(f"{NASA_BASE_URL}/neo/rest/v1/feed", params=params)
        
        if response.status_code == 200:
            data = response.json()
            return NEOFeedResponse(**data)
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"NASA API error: {response.text}"
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Failed to connect to NASA API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up HTTP client on shutdown"""
    await client.aclose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)