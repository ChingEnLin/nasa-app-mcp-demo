#!/usr/bin/env python3
"""
MCP Bridge for NASA API - Connects Kiro to NASA data via MCP protocol
This script extracts the NASA API functionality from main.py and exposes it as MCP tools
"""

import asyncio
import os
import httpx
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Load environment variables
load_dotenv()

# NASA API configuration
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
NASA_BASE_URL = "https://api.nasa.gov"

# HTTP client for NASA API calls
client = httpx.AsyncClient(timeout=30.0)

# Initialize MCP server
server = Server("nasa-mcp-server")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available NASA data tools"""
    return [
        Tool(
            name="get_astronomy_picture",
            description="Get NASA's Astronomy Picture of the Day (APOD)",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (optional, defaults to today)"
                    }
                }
            }
        ),
        Tool(
            name="search_mars_rover_photos",
            description="Search for Mars rover photos by rover, sol (Martian day), and camera",
            inputSchema={
                "type": "object",
                "properties": {
                    "rover": {
                        "type": "string",
                        "description": "Rover name (curiosity, perseverance, opportunity, spirit)",
                        "enum": ["curiosity", "perseverance", "opportunity", "spirit"]
                    },
                    "sol": {
                        "type": "integer",
                        "description": "Martian sol (day) number"
                    },
                    "camera": {
                        "type": "string",
                        "description": "Camera name (optional: FHAZ, RHAZ, MAST, NAVCAM, etc.)"
                    }
                },
                "required": ["rover", "sol"]
            }
        ),
        Tool(
            name="find_near_earth_objects",
            description="Find Near Earth Objects (asteroids and comets) for a date range",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    
    if name == "get_astronomy_picture":
        return await get_astronomy_picture(arguments.get("date"))
    
    elif name == "search_mars_rover_photos":
        return await search_mars_rover_photos(
            arguments["rover"],
            arguments["sol"],
            arguments.get("camera")
        )
    
    elif name == "find_near_earth_objects":
        return await find_near_earth_objects(
            arguments["start_date"],
            arguments["end_date"]
        )
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def get_astronomy_picture(date: Optional[str] = None) -> List[TextContent]:
    """Get NASA's Astronomy Picture of the Day"""
    try:
        params = {"api_key": NASA_API_KEY}
        if date:
            params["date"] = date
            
        response = await client.get(f"{NASA_BASE_URL}/planetary/apod", params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            result = f"""**{data['title']}** ({data['date']})

{data['explanation']}

**Image URL:** {data['url']}
**Media Type:** {data['media_type']}"""
            
            if data.get('hdurl'):
                result += f"\n**HD URL:** {data['hdurl']}"
            if data.get('copyright'):
                result += f"\n**Copyright:** {data['copyright']}"
                
            return [TextContent(type="text", text=result)]
        else:
            return [TextContent(type="text", text=f"NASA API error: {response.text}")]
            
    except httpx.RequestError as e:
        return [TextContent(type="text", text=f"Failed to connect to NASA API: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def search_mars_rover_photos(rover: str, sol: int, camera: Optional[str] = None) -> List[TextContent]:
    """Search for Mars rover photos"""
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
            photos = data.get("photos", [])
            
            if not photos:
                return [TextContent(type="text", text=f"No photos found for {rover} rover on sol {sol}")]
            
            result = f"**Mars Rover Photos - {rover.title()} (Sol {sol})**\n\n"
            result += f"Found {len(photos)} photos:\n\n"
            
            for i, photo in enumerate(photos[:5]):  # Limit to first 5 photos
                result += f"{i+1}. **Camera:** {photo['camera']['full_name']} ({photo['camera']['name']})\n"
                result += f"   **Earth Date:** {photo['earth_date']}\n"
                result += f"   **Image:** {photo['img_src']}\n\n"
            
            if len(photos) > 5:
                result += f"... and {len(photos) - 5} more photos"
                
            return [TextContent(type="text", text=result)]
        else:
            return [TextContent(type="text", text=f"NASA API error: {response.text}")]
            
    except httpx.RequestError as e:
        return [TextContent(type="text", text=f"Failed to connect to NASA API: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def find_near_earth_objects(start_date: str, end_date: str) -> List[TextContent]:
    """Find Near Earth Objects for a date range"""
    try:
        params = {
            "api_key": NASA_API_KEY,
            "start_date": start_date,
            "end_date": end_date
        }
        
        response = await client.get(f"{NASA_BASE_URL}/neo/rest/v1/feed", params=params)
        
        if response.status_code == 200:
            data = response.json()
            element_count = data.get("element_count", 0)
            near_earth_objects = data.get("near_earth_objects", {})
            
            result = f"**Near Earth Objects ({start_date} to {end_date})**\n\n"
            result += f"Total objects found: {element_count}\n\n"
            
            for date, objects in near_earth_objects.items():
                result += f"**{date}:**\n"
                for obj in objects[:3]:  # Limit to first 3 objects per date
                    result += f"- **{obj['name']}** (ID: {obj['id']})\n"
                    result += f"  Potentially hazardous: {'Yes' if obj['is_potentially_hazardous_asteroid'] else 'No'}\n"
                    
                    if obj['close_approach_data']:
                        approach = obj['close_approach_data'][0]
                        result += f"  Miss distance: {approach['miss_distance']['kilometers']} km\n"
                        result += f"  Velocity: {approach['relative_velocity']['kilometers_per_hour']} km/h\n"
                    result += "\n"
                
                if len(objects) > 3:
                    result += f"  ... and {len(objects) - 3} more objects\n\n"
                    
            return [TextContent(type="text", text=result)]
        else:
            return [TextContent(type="text", text=f"NASA API error: {response.text}")]
            
    except httpx.RequestError as e:
        return [TextContent(type="text", text=f"Failed to connect to NASA API: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())