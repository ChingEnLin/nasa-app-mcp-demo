# NASA MCP Server Usage Guide

This document explains how to use the NASA MCP (Model Context Protocol) server with various AI clients and provides example prompts to test the functionality.

## Overview

The NASA MCP server provides three main tools for accessing NASA's public APIs:

1. **`get_astronomy_picture`** - Get NASA's Astronomy Picture of the Day (APOD)
2. **`search_mars_rover_photos`** - Get Mars rover photos by rover, sol, and camera
3. **`find_near_earth_objects`** - Find Near Earth Objects (asteroids/comets) for date ranges

## Quick Start

### 1. Prerequisites

Make sure you have the dependencies installed:
```bash
pip install -r requirements.txt
```

### 2. Test the MCP Server

Test that the MCP server works:
```bash
# This should start the server (use Ctrl+C to stop)
python mcp_bridge.py
```

## Configuration for Different Clients

### Kiro IDE

The MCP server is already configured in `.kiro/settings/mcp.json`. The tools are auto-approved and ready to use in Kiro chat.

### VS Code

Configuration is available in `.vscode/mcp.json`. Different VS Code AI extensions may require different setup methods.

### Claude Desktop

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "nasa-mcp-server": {
      "command": "/path/to/your/project/venv/bin/python",
      "args": ["/path/to/your/project/mcp_bridge.py"]
    }
  }
}
```

### Other MCP Clients

Use the following configuration pattern:
```json
{
  "command": "/path/to/venv/bin/python",
  "args": ["/path/to/mcp_bridge.py"],
  "env": {}
}
```

## Example Prompts to Test the MCP Server

### Astronomy Picture of the Day (APOD)

```
Get today's astronomy picture from NASA
```

```
Show me NASA's astronomy picture for January 1, 2024
```

```
What was NASA's astronomy picture on my birthday? (Use format: YYYY-MM-DD)
```

### Mars Rover Photos

```
Show me Mars rover photos from Curiosity on sol 1000
```

```
Get photos from the Perseverance rover on sol 500 using the MAST camera
```

```
Show me recent photos from the Opportunity rover on sol 2000
```

```
Get hazard avoidance camera photos from Curiosity on sol 1500
```

### Near Earth Objects (NEOs)

```
Find near earth objects for this week
```

```
Show me asteroids and comets that passed by Earth in January 2024
```

```
Find potentially hazardous asteroids from December 1-7, 2023
```

```
What near earth objects are approaching Earth between March 1-15, 2024?
```

### Combined Requests

```
Show me today's astronomy picture and find any near earth objects for this week
```

```
Get Mars rover photos from Curiosity on sol 1000 and tell me about today's astronomy picture
```

## Tool Parameters

### get_astronomy_picture
- **date** (optional): Date in YYYY-MM-DD format. Defaults to today.

### search_mars_rover_photos
- **rover** (required): One of: curiosity, perseverance, opportunity, spirit
- **sol** (required): Martian day number (integer)
- **camera** (optional): Camera name like FHAZ, RHAZ, MAST, NAVCAM, etc.

### find_near_earth_objects
- **start_date** (required): Start date in YYYY-MM-DD format
- **end_date** (required): End date in YYYY-MM-DD format

## Sample Responses

### APOD Response
```
**Crab Nebula** (2024-01-15)

The Crab Nebula is cataloged as M1, the first object on Charles Messier's famous list of things which are not comets...

**Image URL:** https://apod.nasa.gov/apod/image/2401/M1_Hubble_960.jpg
**Media Type:** image
**HD URL:** https://apod.nasa.gov/apod/image/2401/M1_Hubble_3864.jpg
```

### Mars Photos Response
```
**Mars Rover Photos - Curiosity (Sol 1000)**

Found 856 photos:

1. **Camera:** Front Hazard Avoidance Camera (FHAZ)
   **Earth Date:** 2015-05-30
   **Image:** http://mars.jpl.nasa.gov/msl-raw-images/...

2. **Camera:** Mast Camera (MAST)
   **Earth Date:** 2015-05-30
   **Image:** http://mars.jpl.nasa.gov/msl-raw-images/...

... and 854 more photos
```

### NEO Response
```
**Near Earth Objects (2024-01-01 to 2024-01-07)**

Total objects found: 15

**2024-01-01:**
- **2024 AA** (ID: 54418497)
  Potentially hazardous: No
  Miss distance: 610571.843293909 km
  Velocity: 77155.5933716609 km/h

**2024-01-02:**
- **415949 (2001 XY10)** (ID: 2415949)
  Potentially hazardous: No
  Miss distance: 50452409.349026638 km
  Velocity: 57205.8951204341 km/h
```

## Troubleshooting

### Common Issues

1. **"ModuleNotFoundError: No module named 'httpx'"**
   - Make sure you're using the virtual environment Python
   - Check that the MCP configuration points to `venv/bin/python`

2. **"Connection closed" errors**
   - Verify the file paths in your MCP configuration are correct
   - Make sure the virtual environment exists and has dependencies

3. **NASA API errors**
   - Check your internet connection
   - Verify your NASA API key in `.env` (or use DEMO_KEY)
   - Be aware of rate limits (1000 requests/hour)

### Testing the Server Manually

You can test individual components:

```bash
# Test NASA API connectivity
curl "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"

# Test the FastAPI server (if running)
curl "http://localhost:8000/apod"

# Test MCP server (will wait for input)
python mcp_bridge.py
```

## NASA API Information

- **Base URL**: https://api.nasa.gov
- **Default API Key**: DEMO_KEY (1000 requests/hour)
- **Get your own key**: https://api.nasa.gov/ (free, same rate limit but dedicated)
- **Documentation**: https://api.nasa.gov/

## File Structure

```
nasa-app-mcp-demo/
├── mcp_bridge.py           # MCP server implementation
├── main.py                 # FastAPI server (alternative access)
├── .kiro/settings/mcp.json # Kiro MCP configuration
├── .vscode/mcp.json        # VS Code MCP configuration
├── .env.example            # Environment template
├── requirements.txt        # Python dependencies
└── MCP_USAGE.md           # This file
```

## Advanced Usage

### Custom Prompts

You can create more specific requests:

```
Show me high-resolution images from the Curiosity rover's mast camera on sol 1000, and also get today's astronomy picture. If there are any near earth objects this week, include those too.
```

```
I'm writing a blog post about Mars exploration. Get me some recent photos from Perseverance rover (sol 800-900 range) and explain what the different cameras are used for.
```

### Integration with Code

The MCP tools can be used in coding contexts:

```
Help me write a Python script that downloads today's astronomy picture and saves it locally. Use the NASA MCP tools to get the image URL first.
```

```
Create a data analysis script that fetches near earth object data for the past month and identifies the most potentially hazardous asteroids.
```

## Support

If you encounter issues:

1. Check the MCP server logs in your AI client
2. Verify your configuration paths are correct
3. Test the FastAPI server as an alternative: `python main.py`
4. Check NASA API status at https://api.nasa.gov/

The MCP server provides the same data as the FastAPI server but through the MCP protocol for seamless AI integration.